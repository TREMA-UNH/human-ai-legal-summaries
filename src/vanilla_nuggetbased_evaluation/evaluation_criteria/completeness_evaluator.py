from typing import Dict, Optional
import botocore
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
from vanilla_nuggetbased_evaluation.evaluation_pymodels import CompletenessEvaluation

def evaluate_completeness(
        logger,
        truncate_nuggets_for_prompt,
        bedrock_client,
        config,
        nugget_data,
        summary: str,
        print_usage: bool,
        top_n_nuggets: Optional[int],
        mode: str,
        max_threads: int = 4 
) -> Dict:
    """
    Evaluate if the top N most important nuggets are present in the summary, including partial mentions.
    Uses threading to parallelize nugget evaluations.
    """
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((botocore.exceptions.ReadTimeoutError,)),
    )
    def check_nugget_presence(nugget_text: str) -> tuple[float, str]:
        prompt_template = """Evaluate whether the NUGGET is covered in the summary, regardless of where or how it appears.

                           NUGGET:
                           {nugget}

                           SUMMARY:
                           {summary}

                           SCORING:
                           - **2**: The nugget's core legal facts are substantively covered in the summary (dollar amounts, key parties, essential obligations/outcomes), allowing the legal point to be understood even if expressed differently or requiring simple inference.
                           - **1**: The nugget's subject matter is addressed but lacks specific critical details (exact amounts, key qualifiers like "additional," precise characterizations) that could affect legal interpretation or case strategy.
                           - **0**: The nugget's core subject matter or key parties are not mentioned, making it impossible to determine the legal fact occurred.

                           EVALUATION FOCUS:
                           - Assess whether the summary preserves the nugget's legal significance (e.g., impact on damages, liability, or case narrative)
                           - Consider factual accuracy and completeness of key details (dollar amounts, admissions, proper names, contractual obligations, dates, or percentages)
                           - Minor rewording is acceptable if the substance remains intact

                           Respond with:
                           - "presence_score": 0 | 1 | 2
                           - "explanation": 
                               - If score = 0: "Missing [X] could impact case by [specific legal consequence]"
                               - If score = 1: "Missing [this exact information] in '[this exact part(s) of summary]' could impact case by [specific legal consequence]"
                               - If score = 2: "Core legal point sufficiently captured as stated in [these sentences of the summary]."  
                           Keep the explanation concise.
                           - Remember the nugget's information may be spread across multiple sentences in the summary - check the entire summary, not individual sentences
                           """
        
        
        # Truncate nuggets if prompt would be too long
        prompt = prompt_template.format(nugget=nugget_text, summary=summary)
        truncated_nuggets, was_truncated = truncate_nuggets_for_prompt(
            [nugget_text], summary, prompt_template
        )

        if not was_truncated:
            # caching should happen
            pass

        
        if was_truncated:
            logger.warning(f"Nugget truncated for evaluation: {nugget_text}...")
        
        # Use the first (and likely only) truncated nugget
        prompt = prompt_template.format(nugget=truncated_nuggets[0] if truncated_nuggets else nugget_text, summary=summary)
        result = generate_structured_output(
            bedrock_client=bedrock_client,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            tool_schema={
                "type": "object",
                "properties": {
                    "presence_score": {
                        "type": "integer",
                        "enum": [0, 1, 2],
                        "description": "Nugget presence: 0 = not mentioned, 1 = partial, 2 = full"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "What necessary key point is missing in the summary"
                    }
                },
                "required": ["presence_score", "explanation"]
            },
            tool_schema_name="nugget_presence",
            description="Check if nugget is present in summary",
            model_id=config.model_path,
            max_tokens=config.max_tokens,
            print_usage=print_usage,
            obj=CompletenessEvaluation
        )
        
        return result["presence_score"], result["explanation"]

    
    nuggets = nugget_data.values()
    # Evaluate presence of each nugget using ThreadPoolExecutor
    total_score = 0.0
    explanations = []
    
    def process_nugget(nugget: Dict[str,any]) -> tuple[str, float, str]:
        """Helper function to process a single nugget and handle exceptions."""
        try:
            presence_score, explanation = check_nugget_presence(nugget["nugget_text"])
            presence_status = "fully present" if presence_score == 2 else "partially mentioned" if presence_score == 1 else "missing"
            # Update nugget dictionary with evaluation results
            updated_nugget = nugget.copy()  # Avoid modifying original
            updated_nugget.update({
                "presence_score": presence_score,
                "explanation": explanation,
                "presence_status": presence_status
            })
            return updated_nugget, presence_score, explanation, presence_status
            # return nugget, presence_score, explanation, presence_status
        except Exception as e:
            logger.error(f"Failed to evaluate nugget: {nugget}... - {str(e)}")
            return nugget, 0, f"Evaluation failed: {str(e)}", "missing"

    # Process nuggets sequentially to avoid rate limiting
    import time
    results = []
    for i, nugget in enumerate(nuggets):
        logger.info(f"Evaluating nugget {i+1}/{len(nuggets)}")
        result = process_nugget(nugget)
        results.append(result)
        if i < len(nuggets) - 1:  # Don't delay after the last nugget
            time.sleep(2)  # Small delay between nugget evaluations
    
    # Process results in order
    for nugget, presence_score, explanation, presence_status in results:
        print(nugget)
        print(presence_score, explanation)
        total_score += presence_score
        explanations.append({
            "nugget": nugget,
            "presence_score": f"{presence_score}, Nugget {presence_status} in summary",
            "explanation": explanation
        })
    
    # Calculate score (out of 100)
    score = (total_score / (len(nuggets) * 2)) * 100 if nuggets else 0
    
    return {
        "score": score,
        "explanation": f"Completeness score based on total presence score {total_score:.1f}/{(len(nuggets)*2)} for {len(nuggets)} top nuggets in {mode} mode",
        "details": explanations
    }