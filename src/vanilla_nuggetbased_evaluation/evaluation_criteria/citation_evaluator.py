



from citation_retriever.citation_linker import CitationLinker
from citation_retriever.deposition_processor import DepositionProcessor
from citation_retriever.summary_parser import Summary
from llm_conv_segmentation.main import initialize_bedrock_model
from transcript_analysis.models.pymodels import Conversation
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
from vanilla_nuggetbased_evaluation.evaluation_pymodels import CitationEvaluation
from concurrent.futures import ThreadPoolExecutor
import re

def prepend_A_speaker_name(conversation, deposition_text):
    # print(conversation)
    output_lines = []
    A_SPEAKER = conversation.A_SPEAKER
    regex = r"^\s*\d+[:.\s]+\s*(A)\b"
    lines = deposition_text.split("\n")
    for line in lines:
        line = re.sub(regex, lambda m: m.group(0).replace(m.group(1), f"{A_SPEAKER}:"), line)
        output_lines.append(line)
    output_text = "\n".join(output_lines)
    # print("--------")
    # print(f"subset deposition text with speaker: {output_text}")
    return output_text


def process_single_citation(citation_entry, conversation, logger, bedrock_client, config, print_usage, surrounding_text_before=None, surrounding_text_after =None):

    if not citation_entry["is_cited"]:
        return None
    


    summary_fact, deposition_text = citation_entry["summary_fact"], citation_entry["text"]
    deposition_text = prepend_A_speaker_name(conversation, deposition_text)
    prompt = f"""
            According to the following summary fact and its supporting deposition, follow this exact evaluation framework:

            STEP 1 - ACCURACY CHECK:
            Does the summary fact accurately infer from what the deposition text directly states or clearly implies?
            Answer: YES / NO 
            Evidence: [Quote specific phrase from deposition that supports or contradicts]

            STEP 2 - COVERAGE CHECK:
            Does the deposition include all specific details (e.g., dates, locations, actions) mentioned in the summary fact?
            Answer: COVERED / NOT COVERED
            Missing elements (if any): [List what is in the summary fact that is missing in the deposition -- Be concise]

            STEP 3 - SUFFICIENCY CHECK:
            Is the deposition text sufficient to fully establish the summary fact as true without additional evidence?
            Answer: SUFFICIENT / INSUFFICIENT
            Reason: [One sentence explanation why the deposition is not sufficient to support the summary fact.]

            Return results in this exact JSON format:
            {{
            "accuracy": "YES/NO",
            "evidence_quote": "exact supporting/contradicting text from deposition",
            "coverage": "COVERED/NOT COVERED", 
            "missing_elements": ["element1", "element2"] or null,
            "sufficiency": "SUFFICIENT/INSUFFICIENT",
            "sufficiency_reason": "one sentence explanation"
            }}

            Summary Fact: "{summary_fact}\n"
            Supporting Deposition: "{deposition_text}\n"
            """
    

    prompt2 = f"""
            According to the following summary fact, supporting deposition, and surrounding text, evaluate using the following framework based on human criteria:

            STEP 1 - RELEVANCE CHECK:
            Does the deposition discuss the same event or topic as the summary fact?
            Answer: RELEVANT / IRRELEVANT
            Explanation: [One sentence explaining why the deposition is relevant or irrelevant to the summary fact.]

            STEP 2 - SUFFICIENCY CHECK:
            Does the deposition provide enough details to fully support the summary fact without additional evidence? If the details are not in the deposition but are found in the surrounding text (approximately one page before or after), select SUFFICIENT (MINOR DISPLACEMENT).
            Answer: SUFFICIENT / SUFFICIENT (MINOR DISPLACEMENT) / INSUFFICIENT
            Explanation: [One sentence explaining why the deposition is sufficient, sufficient with minor displacement, or insufficient, citing specific details from deposition or surrounding text if applicable.]

            STEP 3 - INSUFFICIENT REASON (if applicable):
            If insufficient, why? (Select all that apply)
            Options: ["Missing A Key Detail", "Needs More Context", "Contradictory Information"]
            Answer: [List applicable reasons or null if sufficient]
            Explanation: [One sentence explaining the selected reasons for insufficiency or stating none apply.]

            Return results in this exact JSON format:
            {{
            "relevance": "RELEVANT/IRRELEVANT",
            "relevance_explanation": "One sentence explanation",
            "sufficiency": "SUFFICIENT/SUFFICIENT (MINOR DISPLACEMENT)/INSUFFICIENT",
            "sufficiency_explanation": "One sentence explanation",
            "minor_displacement_quote": "Exact text from surrounding_text_before or surrounding_text_after if SUFFICIENT (MINOR DISPLACEMENT), otherwise null",
            "insufficient_reason": ["reason1", "reason2"] or null,
            "insufficient_reason_explanation": "One sentence explanation or null"
            }}

            Summary Fact: "{summary_fact}"
            Supporting Deposition: "{deposition_text}"
            Surrounding Text Before (approx. one page before): "{surrounding_text_before}"
            Surrounding Text After (approx. one page after): "{surrounding_text_after}"
            """

    # print(f"citation prompt: {prompt}")
    tool_schema = {
        "type": "object",
        "properties": {
            "accuracy": {"type":"string", "enum":["YES", "NO"]},
            "evidence_quote": {"type":"string"},
            "coverage": {"type": "string", "enum":["COVERED", "NOT COVERED"]},
            "missing_elements": {"type":"string"},
            "sufficiency": {"type":"string", "enum":["SUFFICIENT", "INSUFFICIENT"]},
            "sufficiency_reason": {"type":"string"}

        },
        "required": ["accuracy", "evidence_quote", "coverage", "missing_elements", "sufficiency", "sufficiency_reason"]
    }
    result = generate_structured_output(
        bedrock_client=bedrock_client,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        tool_schema=tool_schema,
        tool_schema_name="citation_evaluation",
        description="Evaluate summary citations",
        model_id=config.model_path,
        max_tokens=config.max_tokens,
        print_usage=print_usage,
        obj=CitationEvaluation

    )
    return{
    "summary_text": summary_fact,
    "deposition_text": deposition_text,
    "accuracy": result.accuracy,
    "evidence_quote": result.evidence_quote,
    "coverage": result.coverage,
    "missing_elements": result.missing_elements,
    "sufficiency": result.sufficiency,
    "sufficiency_reason": result.sufficiency_reason
    }




def evaluate_citations(logger,
                       bedrock_client,
                       config,
                       summary_path: str,
                       conversation: Conversation,
                       deposition_path: str,
                       print_usage: bool,
                       max_workers: int = 4
                       ):

    summary = Summary(summary_path=str(summary_path))
    deposition_processor = DepositionProcessor(deposition_path=str(deposition_path))
    linker = CitationLinker(summary, deposition_processor)

    _, citation_data = linker.link_citations_to_transcript(include_uncited=True)
    """
    citation data format as a dict:
            "citation_id",
            "citation_str",
            "citation_part",
            "start_page",
            "end_page",
            "start_line",
            "end_line",
            "text",
            "link",
            "lines",
            is_cited,
            summary_fact (summary fact text)
            citation_str (summary citation)

    """
    # Group citations by summary fact to handle multi-part citations
    citation_groups = {}
    for citation_entry in citation_data:
        if citation_entry["is_cited"]:
            fact_text = citation_entry["summary_fact"]
            if fact_text not in citation_groups:
                citation_groups[fact_text] = {
                    "citations": [],
                    "citation_str": citation_entry["citation_str"]
                }
            citation_groups[fact_text]["citations"].append(citation_entry)
    
    # Create combined citation entries
    combined_citations = []
    for fact_text, group_data in citation_groups.items():
        citations = group_data["citations"]
        
        # Combine all deposition text for this summary fact
        combined_text = "\n\n".join([c["text"] for c in citations])
        
        # Create a combined citation entry
        combined_entry = {
            "summary_fact": fact_text,
            "text": combined_text,
            "citation_str": group_data["citation_str"],
            "is_cited": True,
            "citation_count": len(citations),  # Track how many citations were combined
            "page_range": f"{min(c['start_page'] for c in citations)}-{max(c['end_page'] or c['start_page'] for c in citations)}"
        }
        combined_citations.append(combined_entry)
    
    output = []

    # Process citations sequentially to avoid rate limiting
    import time
    for i, citation_entry in enumerate(combined_citations):
        logger.info(f"Evaluating citation {i+1}/{len(combined_citations)}")
        result = process_single_citation(citation_entry, conversation, logger, bedrock_client, config, print_usage)
        if result:
            output.append(result)
            logger.debug(f"Completed citation evaluation: {result['summary_text'][:50]}... (combined {result.get('citation_count', 1)} citations)")
        if i < len(combined_citations) - 1:  # Don't delay after the last citation
            time.sleep(2)  # Small delay between citation evaluations
    
    return output

    



def calculate_citation_score(citations):
    """Calculate weighted citation score (0-100 scale)"""
    if not citations:
        return 0.0
    
    total_score = 0
    weights = {
        "accuracy": 0.5,      # 50% - Most important
        "sufficiency": 0.3,   # 30% - Very important  
        "coverage": 0.2   # 20% - Important for context
    }
    
    for citation in citations:
        citation_score = 0
        
        # Accuracy scoring
        if citation.get("accuracy") == "YES":
            citation_score += weights["accuracy"] * 100
        # NO = 0 points
            
        # Sufficiency scoring  
        if citation.get("sufficiency") == "SUFFICIENT":
            citation_score += weights["sufficiency"] * 100
        # INSUFFICIENT = 0 points
            
        # coverage scoring
        if citation.get("coverage") == "COVERED":
            citation_score += weights["coverage"] * 100

        # Not Covered = 0 points
            
        total_score += citation_score
    
    # Average across all citations - .2f precision
    return round((total_score / len(citations)),2) if citations else 0.0