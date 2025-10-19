import re
from typing import Dict, List

from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
from vanilla_nuggetbased_evaluation.evaluation_pymodels import ClarityEvaluation, ConsolidatedNuggetItem


def evaluate_clarity(
                    logger,
                    bedrock_client,
                    config,
                    summary: str, 
                    print_usage: bool
                    ) -> Dict:
    """
    Evaluate clarity of terminology, especially acronyms and other critical clarity issues.
    """
    logger.info("Evaluating clarity of terminology")
    
    # Extract acronyms from both nuggets and summary
    acronym_pattern = r'\b[A-Z]{2,}\b'
    
    summary_acronyms = set(re.findall(acronym_pattern, summary))

    
    prompt_template = """Evaluate terminology clarity in this legal summary, focusing on undefined acronyms and other critical clarity issues for professional readers in legal domain (e.g., attorneys).

        ACRONYMS FOUND: {acronyms}

        SUMMARY: {summary}

        EVALUATION CRITERIA:
        1. UNDEFINED ACRONYMS: Count only the acronyms that are unclear what they refer to when first used
        - EXCLUDE all common acronyms (US, UK, FBI, CEO, etc.)
        - INCLUDE just industry-specific or case-specific acronyms without definition

        2. OTHER CLARITY ISSUES: Identify significant problems that would confuse professional readers:
        - Ambiguous pronouns without clear antecedent
        - Inconsistent terminology
        - Technical terms crucial to understanding but unexplained
        - Complex processes described without sufficient context

        FOCUS: Issues that would genuinely impede comprehension or reduce document credibility for professional readers or people involved in the deposition.

        OUTPUT FORMAT:
        - "unclear_count": Total number of significant clarity issues
        - "explanation": CONCISE description of each issue found, focusing on why it's problematic
        """
    prompt = prompt_template.format(acronyms=list(summary_acronyms), summary=summary)
    result = generate_structured_output(
        bedrock_client=bedrock_client,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        tool_schema={
            "type": "object",
            "properties": {
                "unclear_count": {
                    "type": "integer", 
                    "minimum": 0,
                    "description": "Total number of clarity issues including acronyms and other critical problems"
                },
                "explanation": {
                    "type": "string",
                    "description": "Detailed explanation of all clarity issues found"
                }
            },
            "required": ["unclear_count", "explanation"]
        },
        tool_schema_name="clarity_evaluation",
        description="Evaluate terminology clarity",
        model_id=config.model_path,
        max_tokens=config.max_tokens,
        print_usage=print_usage,
        obj=ClarityEvaluation
    )
    
    # Calculate score from counts
    total_elements = len(summary_acronyms) + len(summary.split())//20  # Rough estimate of clarity checkpoints
    unclear_count = result["unclear_count"]
    clarity_score = 100 if total_elements == 0 else max(0, 100*(total_elements - unclear_count) / total_elements)
    
    return {
        "acronyms": list(summary_acronyms),
        "score": clarity_score,
        "score_detail": f"{unclear_count} clarity issues found affecting readability",
        "explanation": result.explanation,
        "details": {
            "total_acronyms": len(summary_acronyms),
            "total_clarity_issues": unclear_count
        }
    }
