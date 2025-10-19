
from typing import Dict, List
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
from vanilla_nuggetbased_evaluation.evaluation_pymodels import ConsolidatedNuggetItem, StructureEvaluation


def evaluate_structure(logger, bedrock_client, config, summary: str, print_usage: bool) -> Dict:
        """Summary Structure Assessment."""
        

        prompt_template = """
            Answer two simple questions about this legal summary:

            1. Are facts built upon each other logically?
            2. Does it match the declared format from the beginning?

            SUMMARY: {summary}

            Respond with:
            - **logical_flow**: Yes/No
            - **format_compliance**: Yes/No
            - **issues**: String: if either is false, concisely explain what's wrong and how to fix it"""
        
        prompt = prompt_template.format(summary=summary)
        logger.info(f"structure prompt: {prompt}")
        # Get structured response
        result = generate_structured_output(
            bedrock_client=bedrock_client,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            tool_schema={
                "type": "object",
                "properties": {
                    "logical_flow": {"type": "string", "enum":["Yes","No"]},
                    "format_compliance": {"type": "string",  "enum":["Yes","No"]},
                    "issues": {"type": "string"}
                },
                "required": ["logical_flow",  "format_compliance", "issues"]
            },
            tool_schema_name="structure_evaluation",
            description="Evaluate summary structure",
            model_id=config.model_path,
            max_tokens=config.max_tokens,
            print_usage=print_usage,
            obj=StructureEvaluation

        )
        logger.info(f"structure output: {result}")
        logical_flow_bool = result.logical_flow == "Yes"
        format_compliance_bool = result.format_compliance == "Yes"

        return {
            "score": [
                {"structured": format_compliance_bool}, 
                {"logical flow": logical_flow_bool}
            ],
            "explanation": result.issues,
        }
