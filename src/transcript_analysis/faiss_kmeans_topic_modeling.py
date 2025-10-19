import torch
from itertools import islice
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np
import argparse
import json
import faiss
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import matplotlib.colors as mcolors
import os
from transformers import pipeline


torch.manual_seed(0)


def load_model_for_generate(model_name):

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        # device="auto"
        # load_in_4bit = True
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    return model, tokenizer


def generate_topic_name(model, tokenizer, sentences, num_sentences=8):

    sentences = [str(s) for s in sentences if s and isinstance(s, str)]

    # Select up to num_sentences, evenly spaced
    step = max(1, len(sentences) // min(num_sentences, len(sentences)))
    selected_sentences = sentences[::step][:num_sentences]

    # # Create prompt
    # prompt = (
    #     "Given the following sentences from a legal deposition, generate a concise summary that captures their common specific theme:\n\n" +
    #     "\n".join(f"- {s}" for s in selected_sentences) +
    #     "\n\nTopic name:"
    # )

    # Create prompt
    prompt = (
        "From the following sentences taken from a legal deposition, identify and extract 5 concise key facts, focusing on any that mention exhibits, dates, or numerical information.\n\n"
        "\n".join(f"- {s}" for s in selected_sentences) + "\n\nTopic name:"
    )

    inputs = tokenizer(prompt, return_tensors="pt", return_attention_mask=False)

    outputs = model.generate(**inputs, max_new_tokens=512)
    text = tokenizer.batch_decode(outputs)[0]
    print(text[len(prompt) :])
    return text[len(prompt) :]


def get_embd_batched(model, tokenizer, sentences, batch_size=16):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    inputs = tokenizer(
        sentences, return_tensors="pt", padding=True, truncation=True, max_length=512
    )

    inputs = {key: val.to(device) for key, val in inputs.items()}

    embeddings = []
    for i in range(0, len(sentences), batch_size):
        batch_inputs = {key: val[i : i + batch_size] for key, val in inputs.items()}
        with torch.no_grad():
            outputs = model(**batch_inputs, output_hidden_states=True)
            if not hasattr(outputs, "hidden_states"):
                raise ValueError("Model does not support output_hidden_states.")
            last_hidden_state = outputs.hidden_states[-1]
            batch_emb = last_hidden_state.mean(dim=1).to(torch.float32).cpu().numpy()
            # Replace NaN/Inf with zeros
            batch_emb = np.nan_to_num(batch_emb, nan=0.0, posinf=0.0, neginf=0.0)
            embeddings.append(batch_emb)

    return np.concatenate(embeddings, axis=0)


def cluster_sentences(model, tokenizer, sentences, n_clusters=5, batch_size=16):
    print("Start of embedding generation")
    embeddings = get_embd_batched(model, tokenizer, sentences, batch_size).astype(
        "float32"
    )
    print("End of embedding generation")

    # Adjust n_clusters to avoid FAISS warning
    n_clusters = min(n_clusters, len(embeddings) // 39 + 1)
    if n_clusters < 1:
        raise ValueError("Not enough valid embeddings for clustering")

    faiss.normalize_L2(embeddings)
    d = embeddings.shape[1]
    kmeans = faiss.Kmeans(d, n_clusters, niter=20, verbose=True)
    print(f"Training k-means with {n_clusters} clusters...")
    kmeans.train(embeddings)
    _, cluster_assignments = kmeans.index.search(embeddings, 1)

    return cluster_assignments.flatten(), embeddings


def visualize_clusters(
    sentences, cluster_assignments, embeddings, output_file="cluster_plot.png"
):
    if len(sentences) < 2:
        print("Skipping visualization: not enough valid sentences")
        return

    # Ensure perplexity is valid
    perplexity = min(5, len(sentences) - 1)
    tsne = TSNE(n_components=2, random_state=0, perplexity=perplexity)
    # Replace NaN/Inf in embeddings for t-SNE
    embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=0.0, neginf=0.0)
    embeddings_2d = tsne.fit_transform(embeddings)
    colors = list(mcolors.TABLEAU_COLORS.values())[
        : len(np.unique(cluster_assignments))
    ]
    plt.figure(figsize=(10, 8))
    for cluster_id in np.unique(cluster_assignments):
        mask = cluster_assignments == cluster_id
        plt.scatter(
            embeddings_2d[mask, 0],
            embeddings_2d[mask, 1],
            c=[colors[cluster_id]],
            label=f"Cluster {cluster_id}",
            s=100,
        )
    plt.title("Sentence Clustering (t-SNE)", fontsize=14)
    plt.xlabel("t-SNE Dimension 1")
    plt.ylabel("t-SNE Dimension 2")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cluster sentences using Saul-Instruct-v1 embeddings"
    )
    parser.add_argument("--input", type=str, help="Input JSON file with sentences")
    parser.add_argument(
        "--output",
        type=str,
        default="cluster_plot.png",
        help="Output file for cluster visualization",
    )
    parser.add_argument("--n_clusters", type=int, default=4, help="Number of clusters")
    parser.add_argument(
        "--max_fact", type=int, help="Maximum number of facts to process"
    )
    parser.add_argument(
        "--batch_size", type=int, default=16, help="Batch size for embedding generation"
    )
    args = parser.parse_args()

    if not args.input or not os.path.exists(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")
    if args.max_fact is not None and args.max_fact <= 0:
        raise ValueError("max_fact must be positive")

    model_name = "Equall/Saul-Instruct-v1"
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.float32,  # Use float32 to reduce numerical instability
        trust_remote_code=True,
        output_hidden_states=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    sentences = []
    facts = []
    with open(args.input, "r") as jsonin:
        iterable = (
            islice(jsonin, args.max_fact) if args.max_fact is not None else jsonin
        )
        for line in iterable:
            data = json.loads(line)
            sentences.append(data.get("sentence", ""))
            facts.append(data)

    if not sentences:
        raise ValueError("No sentences loaded from input file")

    cluster_assignments, embeddings = cluster_sentences(
        model, tokenizer, sentences, args.n_clusters, args.batch_size
    )
    visualize_clusters(sentences, cluster_assignments, embeddings, args.output)

    if facts:
        # Collect sentences for each cluster
        cluster_sentences = {i: [] for i in range(args.n_clusters)}
        for sentence, cluster_id in zip(sentences, cluster_assignments):
            cluster_sentences[cluster_id].append(sentence)

        model, tokenizer = load_model_for_generate(model_name)
        # Generate topic names for each cluster
        topic_names = {}
        for cluster_id in range(args.n_clusters):
            if len(cluster_sentences[cluster_id]) > 0:
                topic_name = generate_topic_name(
                    model, tokenizer, cluster_sentences[cluster_id]
                )
                topic_names[cluster_id] = topic_name

        # Assign topic names to facts
        for fact, cluster_id in zip(facts, cluster_assignments):
            fact["topic"] = topic_names[cluster_id]

        output_json = args.output.replace(".png", "_facts.json")
        with open(output_json, "w") as jsonout:
            for fact in facts:
                json.dump(fact, jsonout)
                jsonout.write("\n")
