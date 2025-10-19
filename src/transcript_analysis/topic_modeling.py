from pymodels import Sentence, Fact, TopicModelingResult
import argparse
import json
import torch
from outlines import generate, models, samplers
import regex

torch.random.manual_seed(0)
seed = 0


if __name__ == "__main__":

    parser = argparse.ArgumentParser("assigning topic to each line of sentences")
    parser.add_argument(
        "--input", type=str, help="the input file cosisiting of json Facts"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="the output file path cosisiting of json Facts with topics",
    )

    args = parser.parse_args()

    model = models.transformers("microsoft/Phi-3-mini-4k-instruct")

    topics = set()

    with open(args.input, "r") as jsonin, open(args.output, "w") as jsonout:
        lines = list(jsonin)
        for jsonline in lines:
            data_dict = json.loads(jsonline)
            fact = Fact(**data_dict)

            #     prompt = (
            #     "Assign a reusable, one-word topic to the following sentence from a deposition, based on what they are about (obj of the sentence mostly).\n\n"
            #     "The sentence begins with \"#.\":\n\n"
            #     "Use the previously identified topics listed below (each starting with '**') as reference.\n\n"
            #     "THE OUTPUT MUST BE A SINGLE WORD — no numbers, comments, explanations, or signs.\n" \
            #     "Topic:\n"
            # )
            prompt = (
                "What is this deposition sentence about (starting with #)? JUST ONE WORD.\n"
                "You can use the list of options in the following:\n"
                ""
            )

            prompt += (
                "\n".join([f"** {topic}\n" for topic_num, topic in enumerate(topics)])
                if len(topics) > 0
                else ""
            )
            prompt_temp = prompt + f"""# {fact.sentence}\n"""

            print(prompt_temp)

            generator = generate.json(model, TopicModelingResult)
            result_topic = generator(prompt_temp, seed=seed)
            topics.add(result_topic.topic)
            fact.topic = result_topic.topic

            print(f"TOPIC -> {result_topic}")
            json.dump(fact.model_dump(), jsonout)
            jsonout.writelines("\n")


# prompt = f"""
# Write the results of simulating topic modeling for the following documents, each starting with "#."
# # Assume you will identify 2 topics and assign each topic to each sentence.
# # NOTE: Outputs must always be in the format "# sentence: topic" and nothing else.
# {doc_string}"""
