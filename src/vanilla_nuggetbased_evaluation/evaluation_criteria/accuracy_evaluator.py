from typing import Dict, List

from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
from transcript_analysis.qa_fact_generation_chunk.utils.qa_parser_chunk import chunk_summary_facts
from vanilla_nuggetbased_evaluation.evaluation_pymodels import AccuracyEvaluation, GenQuestions



def evaluate_accuracy(
                    logger,
                    truncate_nuggets_for_prompt,
                    bedrock_client,
                    config,
                    mapping: Dict[str, List[Dict[str, str]]],
                    summary: str,
                    print_usage: bool) -> Dict:
        """
        Evaluate if inaccuracy exists
        """

        all_nuggets = [nugget["text"] for nuggets_list in mapping.values() for nugget in nuggets_list]

        if not all_nuggets:
            
            logger.warning("No nuggets provided for accuracy evaluation")
            return {
                "has_inaccuracy": False,
                "explanation": "No nuggets available for evaluation"
            }

        # prompt focusing on errors
        prompt_template = """
            You are verifying the accuracy of a summary against a specific information nugget.

            NUGGETS:
            {nuggets}

            SUMMARY TO EVALUATE:
            {summary}

            TASK: Determine ONLY whether the summary contains factual inaccuracies when representing the information in the nugget. Missing or omitted details DO NOT count as inaccuracies unless they cause a direct contradiction or factual distortion.

            CRITICAL ACCURACY RULES:
            1. EXACT MATCH REQUIRED: All numbers, dates, and specific facts must match EXACTLY between the nugget and summary.
            2. NO ASSUMPTIONS: Do not infer or assume any information not explicitly stated in the nugget.
            3. NO EXTERNAL KNOWLEDGE: Use ONLY the information provided in the nugget and summary.
            4. DO NOT FLAG MISSING INFO: If the summary leaves out part of the nugget but doesn’t contradict it, that is NOT an inaccuracy.

            VERIFICATION STEP:
            Before claiming any inaccuracy, you MUST:
            1. Quote the relevant parts of both the nugget and summary side by side.
            2. Highlight the specific discrepancy.

            Respond with:
            - "has_inaccuracy": true or false
            - "explanation": A brief, fact-based explanation of why the summary is or isn't accurate. If accurate, simply state that all information matches. If inaccurate, provide the side-by-side quotes and highlight the discrepancy."""
        
        formatted_nuggets = [f"nugget_{i+1}: {nugget}\n" for i, nugget in enumerate(all_nuggets)]

        truncated_nuggets, was_truncated = truncate_nuggets_for_prompt(
            formatted_nuggets, summary, prompt_template
        )

        if was_truncated:
            logger.warning(f"Nuggets truncated for evaluation: {', '.join(truncated_nuggets[:2])}...")

        # Use truncated nuggets if available and not empty, otherwise use formatted nuggets
        nuggets_to_use = truncated_nuggets if truncated_nuggets else formatted_nuggets
        
        prompt = prompt_template.format(
            nuggets="\n".join(nuggets_to_use),
            summary=summary
        )
        logger.info(f"accuracy prompt:{prompt}")
        tool_schema = {
            "type": "object",
            "properties": {
                "has_inaccuracy": {"type": "boolean"},
                "explanation": {"type": "string"}
            },
            "required": ["has_inaccuracy", "explanation"]
        }

        try:
            results = generate_structured_output(
                bedrock_client=bedrock_client,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                tool_schema=tool_schema,
                tool_schema_name="accuracy_evaluation",
                description="Check if inaccuracy is in summary",
                model_id=config.model_path,
                max_tokens=config.max_tokens,
                print_usage=print_usage,
                obj=AccuracyEvaluation
            )

            return {
                "has_inaccuracy": results.has_inaccuracy,
                "score": 100.0 if not results.has_inaccuracy else 0.0,
                "explanation": results.explanation
            }


        except Exception as e:
            logger.error(f"Accuracy evaluation failed: {e}")
            raise





def evaluate_accuracy_with_deposition(self,
                        mapping: Dict[str, List[Dict[str, str]]],
                        summary: str,
                        print_usage: bool) -> Dict:
    """
    Evaluate if inaccuracy exists comparing the summary to the whole deposition
    """

    all_summary_facts = [{f"Fact_{i}":fact} for i,fact in enumerate(summary.split("\n"))]

    if not all_summary_facts:
        self.logger.warning("No nuggets provided for accuracy evaluation")
        return {
            "has_inaccuracy": False,
            "explanation": "No nuggets available for evaluation"
        }

    # prompt focusing on errors
    prompt_template = """
        You are generating close-ended questions to verify factual accuracy of a summary.

        FACTS:
        {all_summary_facts}

        TASK: 
        Generate verification questions for ONLY the specific, verifiable claims in the facts above.

        QUESTION TYPES TO CREATE:
        1. **Yes/No questions** - for actions, decisions, or binary claims
        2. **Specific value questions** - for dates, numbers, amounts, names
        3. **Verification questions** - for quoted statements or direct claims

        RULES:
        - Focus on factual claims that can be verified against source documents
        - Avoid interpretive or subjective questions
        - Each question should test ONE specific fact
        - Include enough context so the question is clear

        OUTPUT FORMAT:
        Question: [your question]
        Type: [Yes/No | Specific Value | Verification]
        Answer: [answer to the question according to the FACTS]

        Generate questions for the key factual claims above:
        """
    
    
    all_summary_facts = [{"Fact_{}".format(i): fact} for i, fact in enumerate(summary.split("\n"))]
    fact_chunks = chunk_summary_facts(all_summary_facts, chunk_size=4000, overlap=2)

    tool_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "type": {"type": "string", "enum": ["Yes/No", "Specific Value", "Verification"]},
                "answer": {"type":"string"}
            },
            "required": ["question", "type"]
        }
    }


    all_questions = []

    # Process each chunk
    for chunk_idx, fact_chunk in enumerate(fact_chunks):
        chunk_facts_str = json.dumps(fact_chunk, indent=2)
        
        try:
            # Generate questions for this chunk
            response = generate_structured_output(
            bedrock_client=self.bedrock_client,
            messages=[{"role": "user", "content": [{"text": prompt_template.format(all_summary_facts=chunk_facts_str)}]}],
            tool_schema=tool_schema,
            tool_schema_name="question_generator",
            description="generate questions for facts (chunk of facts) in the summary",
            model_id=self.config.model_path,
            max_tokens=self.config.max_tokens,
            print_usage=print_usage,
            obj=GenQuestions
            )
            
            
            if response and isinstance(response, list):
                all_questions.extend(response)
            
        except Exception as e:
            self.logger.error(f"Error generating questions for chunk {chunk_idx}: {str(e)}")
            continue

    # Now verify each question against the deposition
    accuracy_results = []
    has_inaccuracy = False
    
    for question_data in all_questions:
        question = question_data.get("question", "")
        question_type = question_data.get("type", "")
        
        # Retrieve relevant passages from deposition
        retrieved_passages = self._retrieve_relevant_passages(question, mapping)
        
        # Answer the question based on retrieved passages
        answer_result = self._answer_question_from_passages(question, retrieved_passages)
        
        # Compare with summary expectation
        comparison_result = self._compare_answers(question, answer_result, summary)
        
        accuracy_results.append({
            "question": question,
            "type": question_type,
            "retrieved_passages": len(retrieved_passages),
            "answer_status": comparison_result["status"],  # "match", "neutral", "contradiction"
            "explanation": comparison_result["explanation"]
        })
        
        if comparison_result["status"] == "contradiction":
            has_inaccuracy = True

    # Generate final explanation
    contradictions = [r for r in accuracy_results if r["answer_status"] == "contradiction"]
    
    if has_inaccuracy:
        explanation = f"Found {len(contradictions)} contradictions in the summary. "
        explanation += "Key issues: " + "; ".join([c["explanation"] for c in contradictions[:3]])
    else:
        explanation = f"No contradictions found. Verified {len(all_questions)} factual claims."

    return {
        "has_inaccuracy": has_inaccuracy,
        "explanation": explanation,
        "questions_generated": len(all_questions),
        "contradictions_found": len(contradictions),
        "detailed_results": accuracy_results
    }

