from transformers import pipeline
import torch


def generate_topic_name(sentences, num_sentences=8):
    if not sentences:
        return "Empty Cluster"

    # Validate and filter sentences
    sentences = [str(s) for s in sentences if s and isinstance(s, str)]
    if not sentences:
        return "Empty Cluster"

    # Select up to num_sentences, evenly spaced
    step = max(1, len(sentences) // min(num_sentences, len(sentences)))
    selected_sentences = sentences[::step][:num_sentences]

    # Create prompt
    prompt = (
        "Given the following sentences from a legal deposition, generate a concise topic name (up to 5 words) that captures their common theme:\n\n"
        + "\n".join(f"- {s}" for s in selected_sentences)
        + "\n\nTopic name:"
    )

    try:
        # Initialize pipeline with safer settings
        pipe = pipeline(
            "text-generation",
            model="Equall/Saul-Instruct-v1",
            torch_dtype=(
                torch.float16 if torch.cuda.is_available() else torch.float32
            ),  # Use float16 on GPU
            device_map="auto",
            model_kwargs={"low_cpu_mem_usage": True},
        )

        # Apply chat template
        messages = [{"role": "user", "content": prompt}]
        prompt = pipe.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # Generate output
        outputs = pipe(
            prompt,
            max_new_tokens=30,  # Increased for flexibility
            do_sample=False,
            pad_token_id=pipe.tokenizer.pad_token_id,
            eos_token_id=pipe.tokenizer.eos_token_id,
            return_full_text=False,
        )

        # Extract topic name
        generated_text = outputs[0]["generated_text"].strip()
        topic_name = (
            generated_text.split("Topic name:")[-1].strip()
            if "Topic name:" in generated_text
            else generated_text
        )
        topic_name = " ".join(topic_name.split()[:5])  # Limit to 5 words
        return topic_name if topic_name else "Unnamed Topic"

    except RuntimeError as e:
        print(f"Runtime error in generate_topic_name: {str(e)}")
        return "Error Topic"
    except ValueError as e:
        print(f"Value error in generate_topic_name: {str(e)}")
        return "Error Topic"
    except Exception as e:
        print(f"Unexpected error in generate_topic_name: {str(e)}")
        return "Error Topic"


sentences = [
    "The witness described the contract terms.",
    "The agreement was signed in 2023.",
    "The dispute arose over payment delays.",
    "Legal counsel reviewed the documents.",
    "The deposition focused on contract breaches.",
]
topic = generate_topic_name(sentences)
print(topic)  # Expected: e.g., "Contract Disputes"
