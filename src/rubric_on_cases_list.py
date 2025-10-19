from pydantic import BaseModel
from typing import Optional, Dict, List
import pandas as pd
from outlines import generate, models
import json
import torch
import argparse

seed = 0
global rubric_generation_prompt


class OneTopicRubric(BaseModel):

    title: str
    questions: List[str]

    def __str__(self):
        return f"Title: {self.title}\nQuestions:\n\t" + "\n\t".join(self.questions)


class AllRubricQuestions(BaseModel):

    all: List[OneTopicRubric]

    def __str__(self):
        return "\n".join(str(topic) for topic in self.all)


class KeyWords(BaseModel):

    keywords: List[str]


class Case(BaseModel):

    super_category: str
    code: str
    key_words: Optional[List[str]] = None
    rubric: Optional[AllRubricQuestions] = None

    def __str__(self):
        rubric_str = f"\nRubric:\n{self.rubric}" if self.rubric else ""

        return (
            f"SuperCategory:{self.super_category}\n"
            f"Code: {self.code}\n"
            f"Keywords: {self.key_words}"
            f"Rubric: {rubric_str}"
        )


class Prompts:
    prompts: List[str] = [
        # 0
        """Identify and list the most important and contextually relevant questions that a legal deposition should be able to answer in a case categorized under '{super_category}', with a specific focus on the issue represented by '{code}'. 
    The questions should be organized in a logical, hierarchical structure — beginning with background and foundational facts, and progressing toward legal responsibility, factual causation, claimed harm or damages (if applicable), and any defenses or mitigating factors.
    Ensure the structure is adaptable to both liability-focused and remedy-focused cases.""",
        # 1
        """Identify and list the most important and contextually relevant questions that a legal deposition should be able to answer in a case classified under '{super_category}', focusing specifically on the issue represented by '{code}'. Organize the questions in a logical, hierarchical structure.""",
        # 2
        """Identify and list the most important and contextually relevant questions that an attorney is seeking answwer for in a legal deposition in a case classified under '{super_category}', focusing specifically on the issue represented by '{code}'. Organize the questions in a logical, hierarchical structure.""",
        # 3
        """Generate a concise list of key questions that an attorney would ask during a legal deposition for a case under the deposition type '{super_category}', focusing on the specific issue '{code}'. The questions should:
    - Target critical facts, evidence, or legal arguments relevant to the specific issue ({code}) within the broader deposition type ({super_category}).
    - Be clear, precise, and designed to extract actionable insights from a deposition summary.
    - Cover key legal elements (e.g., liability, causation, damages, defenses) without redundancy.
    - Be organized hierarchically under titled sections corresponding to legal elements or topics (e.g., 'Liability', 'Damages', 'Causation', 'Defenses').
    Format the output as a structured list with titled sections, each containing 1–3 questions. Use numbered questions under each title.""",
        # 4
        """Generate a concise list of 5–8 universal questions that an attorney would ask in every legal deposition for a case under the deposition type '{super_category}', focusing on the specific issue '{code}'. The questions should:
    - Target critical facts, evidence, or legal arguments that are essential for every deposition in this category and must be addressed in the deposition summary.
    - Be clear, precise, and broadly applicable to all cases under the specified '{code}' within '{super_category}'.
    - Cover key legal elements (e.g., liability, causation, damages, defenses) without redundancy.
    - Be organized hierarchically under titled sections corresponding to legal elements or topics (e.g., 'Liability', 'Damages', 'Causation', 'Defenses'), with 1–3 questions per section.
    Format the output as a structured list with titled sections, each containing numbered questions. Avoid including explanations or case-specific details beyond the scope of '{code}'.""",
        # 5
        """Generate a concise list of 5–8 universal questions that an attorney would ask in every legal deposition "
            "for a case under the deposition type '{super_category}', focusing on the specific issue '{code}'. The questions should: "
            "- Target practical, recurring details that are commonly addressed in every deposition for this case type. "
            "- Be clear, precise, and broadly applicable to all cases under '{code}' within '{super_category}'. "
            "- Be organized hierarchically under titled sections with 1–3 questions per section.""",
    ]


def generate_keywords(model: str, super_category: str, code: str):
    generator = generate.json(model, KeyWords)
    prompt = f"""Identify and list the most important and contextually relevant keywords for a legal/technical case under the category "{super_category}", with a focus on the specific issue represented by "{code}". Ensure the keywords reflect core concepts, entities, and terminology commonly associated with this topic."""
    print(prompt)
    keywords = generator(prompt, seed=seed)
    return keywords


def generate_rubric(model, prompt: str, super_category: str, code: str):
    generator = generate.json(model, AllRubricQuestions)
    prompt = prompt.format(super_category=super_category, code=code)
    print(prompt)
    questions = generator(prompt, seed=seed, max_tokens=4000)
    return questions


def main():

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device = {device}")

    parser = argparse.ArgumentParser(
        "generate rubric for each case categiry-subcategory"
    )
    parser.add_argument("--input", type=str, help="the csv file of all cases")
    parser.add_argument("--output", type=str, help="the output json file")
    parser.add_argument(
        "--model_path",
        default="microsoft/Phi-3-mini-4k-instruct",
        type=str,
        help="model name / path",
    )
    parser.add_argument(
        "-p", "--prompt_idx", type=int, help="delete later - index of the prompt"
    )

    args = parser.parse_args()
    cases_file_path, output_path, model_path, prompt = (
        args.input,
        args.output,
        args.model_path,
        Prompts.prompts[int(args.prompt_idx)],
    )

    cases_file_path = "/home/nf1104/work/Summer 25/nextpoint/Summarization-SHARED-EXTERNALLY/data/20250505 Court Listener Hits on Each Nature of Suit Code - Sheet1.csv"
    output_path = "./all_cases_2.jsonl"
    model_path = "microsoft/Phi-3-mini-4k-instruct"
    # model_path = "HuggingFaceTB/SmolLM2-360M-Instruct"

    model = models.transformers(model_path, device=device)

    data = pd.read_csv(cases_file_path, header=0)
    with open(output_path, "w") as jsonout:
        json.dump(
            {
                "input": cases_file_path,
                "output": output_path,
                "model": model_path,
                "prompt": prompt,
            },
            jsonout,
        )
        for _, row in data.iterrows():
            super_category = row.iloc[0]

            code = row.iloc[1]

            # keywords = generate_keywords(model = model, super_category=super_category, code=code).keywords
            rubric = generate_rubric(
                model=model, prompt=prompt, super_category=super_category, code=code
            )
            case = Case(
                super_category=super_category, code=code, key_words=None, rubric=rubric
            )
            print(case)
            json.dump(case.model_dump(), jsonout)
            # break


if __name__ == "__main__":
    main()
