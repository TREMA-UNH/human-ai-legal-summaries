# from outlines import models, generate
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import boto3
import botocore
from src.vanilla_nuggetbased_evaluation.evaluation_pymodels import ConsolidatedNuggetItem, ConsolidatedNuggetsTemp, Nugget, NuggetData, NuggetsList
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
import logging
import json
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from botocore.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)



def generate_nuggets_for_all_chunks(chunks,
                                    mode:str,
                                    bedrock_client,
                                    CONFIG: Config,
                                    print_usage: bool):
    
    all_nuggets = {}
    # Use threads (I/O-bound task) - using inference profiles for better rate limits
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(
                generate_nuggets_for_a_chunk,
                bedrock_client,
                CONFIG,
                print_usage,
                chunk
            ): idx
            for idx, chunk in enumerate(chunks)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                all_nuggets.update({
                    f"nugget{i + len(all_nuggets)}": 
                    
                    nugget.to_dict()
                    for i, nugget in enumerate(result.nuggets)
                })
            except Exception as e:
                logger.error(f"Chunk {idx} failed: {e}")

    return all_nuggets

def generate_nuggets_for_a_chunk(
    bedrock_client,
    CONFIG,
    print_usage: bool,
    pairs: List[dict], #chunk
) -> NuggetsList:
    """Process question-answer pairs using the Converse API with context from previous annotations."""


    if not pairs:
        raise ValueError("Input pairs list cannot be empty")
    for pair in pairs:
        if not isinstance(pair, dict) or "q" not in pair or "a" not in pair:
            raise ValueError(f"Invalid pair format: {pair}. Expected dict with 'q' and 'a' keys")
        
    
    prompt = (
        f"""You are extracting the most legally significant factual nuggets from deposition question-answer pairs.

        LEGALLY SIGNIFICANT CRITERIA:
        1. **Business Entities & Corporate Information**: Company names, business relationships, corporate structures, partnerships, LLCs, trusts, professional services firms
        2. **Financial Data**: Dollar amounts, measurements, percentages, quantiles, valuations, insurance policies, debts, assets
        3. **Legal Admissions**: Fault, liability, wrongdoing, violations, breaches, disputes
        4. **Key Individuals**: Proper names of people, their roles, relationships, professional titles
        5. **Contractual & Legal Matters**: Obligations, violations, agreements, legal documents, estate planning instruments
        6. **Temporal Information**: Dates, times, timeframes, sequences of events
        7. **Locations & Documents**: Places, addresses, document titles, case names
        8. **Uncertainty & Knowledge Gaps**: Statements indicating lack of knowledge, uncertainty, inability to recall, "I don't know," "I'm not sure," conflicting recollections
        9. **Contradictions & Conflicts**: Inconsistent statements, conflicting testimony, disputes between parties, disagreements about facts or interpretations


        DO NOT INCLUDE NUGGETS ABOUT:\n
        - Routine personal/business information
        - Undisputed background facts
        - Standard procedural information
        - General biographical details

        FORMAT REQUIREMENTS:\n
        - Use witness name from 'a' field (before colon), or 'The witness' if unclear\n
        - Write as standalone, third-person factual nugget\n
        - Spell out acronyms unless the full name isn't mentioned in the deposition\n

        DATA ACCURACY:\n
        - Copy ALL numbers, dates, times, amounts, and measurements EXACTLY as written\n
        - Never calculate, convert, round, or reformat numerical data\n
        - When uncertain about a figure, omit it rather than guess\n\n


        LOCATION TRACKING:
        - Each Q&A pair includes page and line numbers (q_page, q_line for questions; a_page, a_line for answers)
        - For each nugget, identify the source location range:
        * from_page/from_line: Where the nugget information starts (typically the question's location)
        * to_page/to_line: Where the nugget information ends (typically the answer's location)
        - If a nugget spans multiple Q&A pairs, use the first question's location as "from" and the last answer's location as "to" so the lines are completely sufficient to support the nugget.


        OUTPUT:
        - Return a JSON object with a "nuggets" array
        - Each nugget must include: nugget text, from_page, from_line, to_page, to_line
        - Extract exactly two concise nuggets if available. If fewer than four nuggets meet the criteria, include only those that qualify. If none qualify, return empty array."""
        "DEPOSITION DATA:\n" + json.dumps(pairs, indent=2)
    )

    tool_schema = {
        "type": "object", 
        "properties": {
            "nuggets": { 
                "type": "array",  
                "items": {
                    "type": "object",
                    "properties": {
                        "nugget": {
                            "type": "string",
                            "description": "A concise one-line summary of an investigative nugget"
                        },
                        "from_page": {
                            "type": "integer",
                            "description": "Starting page number where the nugget information begins"
                        },
                        "from_line": {
                            "type": "integer", 
                            "description": "Starting line number where the nugget information begins"
                        },
                        "to_page": {
                            "type": "integer",
                            "description": "Ending page number where the nugget information ends"
                        },
                        "to_line": {
                            "type": "integer",
                            "description": "Ending line number where the nugget information ends"
                        }
                    },
                    "required": ["nugget", "from_page", "from_line", "to_page", "to_line"]
                },
                "minItems": 1, 
                "maxItems": 4
            }
        }
    }

    logger.info("Extracting nuggets from chunk")
    try:
        result = generate_structured_output(
            bedrock_client=bedrock_client,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            tool_schema=tool_schema,
            tool_schema_name="extract_nuggets",
            description="Extract factual nuggets from Q&A pairs",
            model_id=CONFIG.model_path,
            max_tokens=CONFIG.max_tokens,
            print_usage=print_usage,
            obj=NuggetsList
        )
        logger.info(f"Extracted nuggets: {result}")
        return result
    except ValidationError as e:
        logger.error(f"Pydantic validation error in extract_nuggets_from_chunk: {e}")
        raise



# *************************************************  consolidate nuggets  *********************************************



def consolidate_nuggets(
    bedrock_client,
    CONFIG,
    print_usage: bool,
    nuggets_dict,
    max_chunk_size: int = 4000,
    second_consolidation_threshold: int = 15,
    max_workers: int = 4
) -> Dict:
    """Consolidate overlapping nuggets into broader factual statements."""
    def chunk_nuggets_by_size(nuggets_dict: Dict[str, str], max_size: int) -> List[Dict[str, str]]:
        if not nuggets_dict:
            raise ValueError("nuggets_dict cannot be empty")
        if max_size <= 0:
            raise ValueError(f"max_size must be positive, got {max_size}")

        chunks = []
        current_chunk = {}
        current_size = 0
        
        for nugget_id, nugget_text in nuggets_dict.items():
            if not (isinstance(nugget_id, str) and isinstance(nugget_text, str)):
                raise ValueError(f"Invalid nugget: ID={nugget_id}, text={nugget_text}")

            item_size = len(json.dumps({nugget_id: nugget_text}))
            
            if current_size + item_size > max_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = {nugget_id: nugget_text}
                current_size = item_size
            else:
                current_chunk[nugget_id] = nugget_text
                current_size += item_size
        
        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"Created {len(chunks)} chunks from {len(nuggets_dict)} nuggets")
        return chunks

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=20),
        retry=retry_if_exception_type((botocore.exceptions.ReadTimeoutError,)),
        reraise=True
    )
    def consolidate_chunk(chunk: Dict[str, str]) -> ConsolidatedNuggetsTemp:
        if not chunk:
            raise ValueError("Chunk cannot be empty")
        for nugget_id, text in chunk.items():
            if not (isinstance(nugget_id, str) and isinstance(text, str)):
                raise ValueError(f"Invalid chunk entry: ID={nugget_id}, text={text}")
        prompt = (
            "You are consolidating factual nuggets from a legal deposition transcript into prioritized, comprehensive statements.\n\n"

            "GROUPING RULES (apply in this priority order):\n"
            "1. Merge nuggets that contain the same proper nouns (person name, company name, document title). Consider variations (e.g., ‘Acme Corp’ and ‘Acme Corporation’) as identical only if the full name is explicitly the same in the data; otherwise, keep separate.\n"
            "2. Merge nuggets that contain the exact same date (MM/DD/YYYY format).\n"
            "3. Merge nuggets that contain the exact same dollar amount or percentage.\n"
            "4. If none of the above apply, keep nuggets separate.\n\n"

            "DATA ACCURACY REQUIREMENTS:\n"
            "- Copy ALL numbers, dates, times, amounts, and measurements EXACTLY as written.\n"
            "- Never calculate, convert, round, or reformat numerical data.\n"
            "- When uncertain about a figure, omit it rather than guess.\n\n"

            "FINAL ORDERING RULES:\n"
            "1. Sort consolidated nuggets by importance category (Dollar Amounts and Admissions first, then Proper Names and Contractual Obligations, then Dates and Percentages).\n"

            "OUTPUT FORMAT:\n"
            "- Third-person factual statements with specific details.\n"
            "- Use witness name from original data, or 'The witness' if unclear.\n\n"

            "OUTPUT: JSON with:\n"
            "1. 'clustered_nuggets': array of consolidated nuggets, ordered by the final ordering rules.\n"
            "2. 'mapping': object mapping each consolidated nugget to original IDs.\n\n"

            "NUGGETS TO CONSOLIDATE:\n" + json.dumps(chunk, indent=2)
)
        tool_schema = {
            "type": "object",
            "properties": {
                "consolidated_nuggets": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "A consolidated investigative nugget combining multiple related nuggets"
                    }
                },
                "mapping": {
                    "type": "object",
                    "description": "Maps each consolidated nugget to the original nugget IDs that were merged",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Original nugget ID (e.g., 'nugget_0')"
                        }
                    }
                }
            },
            "required": ["consolidated_nuggets", "mapping"]
        }

        logger.info(f"Consolidating chunk with {len(chunk)} nuggets, size: {len(json.dumps(chunk))} characters")
        try:
            result = generate_structured_output(
                bedrock_client=bedrock_client,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                tool_schema=tool_schema,
                tool_schema_name="consolidate_nuggets",
                description="Consolidate related nuggets",
                model_id=CONFIG.model_path,
                max_tokens=CONFIG.max_tokens,
                print_usage=print_usage,
                obj=ConsolidatedNuggetsTemp
            )
            logger.info(f"Consolidated chunk result: {result}")
            return result
        except ValidationError as e:
            logger.error(f"Pydantic validation error in consolidate_chunk: {e}")
            raise

    def merge_consolidated_results(chunk_results: List[ConsolidatedNuggetsTemp],
                                  nuggets_dict: Dict[str, str]) -> NuggetData:
        if not chunk_results:
            raise ValueError("chunk_results cannot be empty")
        if not nuggets_dict:
            raise ValueError("nuggets_dict cannot be empty")

        all_nuggets = []
        all_mappings = {}
        nugget_counter = 0

        for result in chunk_results:
            for nugget_text in result.consolidated_nuggets:
                consolidated_id = f"C{nugget_counter}"
                all_nuggets.append(ConsolidatedNuggetItem(consolidated_id=consolidated_id, text=nugget_text))
                all_mappings[consolidated_id] = [
                    {"nugget_id": orig_id, "text": nuggets_dict.get(orig_id, "Unknown")}
                    for orig_id in result.mapping.get(nugget_text, [])
                ]
                nugget_counter += 1

        logger.info(f"Merged {len(all_nuggets)} nuggets from {len(chunk_results)} chunks")

        if len(all_nuggets) > second_consolidation_threshold:
            logger.info(f"Performing final consolidation on {len(all_nuggets)} nuggets")
            nugget_dict = {nugget.consolidated_id: nugget.text for nugget in all_nuggets}
            final_chunks = chunk_nuggets_by_size(nugget_dict, max_size=4000)

            final_nuggets = []
            final_mapping = {}

            for i, chunk in enumerate(final_chunks):
                logger.info(f"Final consolidation chunk {i+1}/{len(final_chunks)}")
                final_result = consolidate_chunk(chunk)
                for nugget_text in final_result.consolidated_nuggets:
                    new_id = f"C{nugget_counter}"
                    final_nuggets.append(ConsolidatedNuggetItem(consolidated_id=new_id, text=nugget_text))
                    original_nuggets = []
                    for orig_nugget_id in final_result.mapping.get(nugget_text, []):
                        original_nuggets.extend(all_mappings.get(orig_nugget_id, []))
                    final_mapping[new_id] = original_nuggets
                    nugget_counter += 1
                
            return NuggetData(
                consolidated_nuggets=final_nuggets,
                mapping=final_mapping
            )
        else:
            return NuggetData(
                consolidated_nuggets=all_nuggets,
                mapping=all_mappings
            )

    logger.info(f"Consolidating {len(nuggets_dict)} nuggets")
    
    chunks = chunk_nuggets_by_size(nuggets_dict, max_chunk_size)
    logger.info(f"Split into {len(chunks)} chunks")
    
    # Process chunks in parallel
    chunk_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {
            executor.submit(consolidate_chunk, chunk): chunk
            for chunk in chunks
        }
        for i, future in enumerate(as_completed(future_to_chunk)):
            chunk = future_to_chunk[future]
            try:
                result = future.result()
                chunk_results.append(result)
                logger.info(f"Chunk {i+1} results: {result}")
            except Exception as e:
                logger.error(f"Chunk {i+1} failed: {e}")
                raise

    final_results = merge_consolidated_results(chunk_results, nuggets_dict)

    formatted_results = {
        "consolidated_nuggets": [
            {"consolidated_id": nugget.consolidated_id, "text": nugget.text}
            for nugget in final_results.consolidated_nuggets
        ],
        "mapping": {
            nugget.consolidated_id: [
                {"nugget_id": orig_nugget.nugget_id, "text": orig_nugget.text}
                for orig_nugget in final_results.mapping[nugget.consolidated_id]
            ]
            for nugget in final_results.consolidated_nuggets
        }
    }
    
    logger.info(f"Final consolidation: {len(final_results.consolidated_nuggets)} nuggets")
    return formatted_results