import uuid
from backend.log_pipeline import log_pipeline_run
from src.citation_retriever.citation_linker import CitationLinker
from src.citation_retriever.deposition_processor import DepositionProcessor
from src.citation_retriever.summary_parser import Summary
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles


import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import json

from src.transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file
from src.vanilla_nugget_generation.DepositionNuggetGeneration import DepositionNuggetGenerator
from src.vanilla_nuggetbased_evaluation.predefined_nuggetbased_evaluation import EnhancedSummaryEvaluator

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODE="mapping"
CSV_LOG_PATH = "./deposition-pipeline-ui_/public/evaluation_pipeline_run_log.csv"

# Schema for process-deposition request
class ProcessDepositionRequest(BaseModel):
    case_name: str
    deposition_filename: str


class GetDepositionRequest(BaseModel):
    case_name: str
    deposition_filename: str

# Schema for one deposition item
class DepositionItem(BaseModel):
    citation_id: Optional[str]
    citation_str: Optional[str]
    start_page: Optional[int]
    end_page: Optional[int]
    start_line: Optional[int]
    end_line: Optional[int]
    text: str
    link: str
    is_cited: bool
    lines: List[tuple]

# Schema for process-pair request
class ProcessPairRequest(BaseModel):
    case_name: str
    deposition_filename: str
    summary_filename: str

# Ensure results directories exist
NUGGETS_DIR = Path("./results/nuggets")
EVALUATION_DIR = Path("./results/evaluation")
NUGGETS_DIR.mkdir(parents=True, exist_ok=True)
EVALUATION_DIR.mkdir(parents=True, exist_ok=True)




app.mount("/annotations", StaticFiles(directory="annotations"), name="annotations")

ANNOTATION_DIR = "annotations"

os.makedirs(ANNOTATION_DIR, exist_ok=True)











# Base directory for paired files
BASE_DIR = Path("./paird depo-summaries")








@app.get("/api/depositions")
async def list_depositions():
    """List all deposition files from the paired depo-summaries directory."""
    try:
        depositions = []
        
        # Scan case directories (01, 02, etc.)
        for case_dir in BASE_DIR.iterdir():
            if case_dir.is_dir():
                case_name = case_dir.name
                # Find deposition files (assume one per case, ends with .txt)
                deposition_files = [f for f in case_dir.glob("*.txt") if f.is_file()]
                
                if deposition_files:
                    for deposition_file in deposition_files:
                        depositions.append({
                            "case_name": case_name,
                            "deposition_name": deposition_file.name,
                            "deposition_id": f"{case_name}_{deposition_file.name}"
                        })
        
        depositions.sort(key=lambda x: x['case_name'])
        return JSONResponse(content={"status": "success", "depositions": depositions})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing depositions: {str(e)}")

@app.get("/api/file-pairs")
async def list_file_pairs():
    """List all deposition and summary file pairs from the paired depo-summaries directory."""
    try:
        pairs = []
        
        # Scan case directories (01, 02, etc.)
        for case_dir in BASE_DIR.iterdir():
            if case_dir.is_dir():
                case_name = case_dir.name
                # Find deposition file (assume one per case, ends with .txt)
                deposition_files = [f.name for f in case_dir.glob("*.txt") if f.is_file()]
                # Find summary files in summaries subfolder
                summary_dir = case_dir / "summaries"
                summary_files = [f.name for f in summary_dir.glob("*.txt")] if summary_dir.exists() else []
                
                if deposition_files and summary_files:
                    deposition = deposition_files[0]  # Assume one deposition per case
                    # Pair deposition with each summary
                    for summary in summary_files:
                        # print(f"{case_name}_{deposition}_{summary}")
                        pairs.append({
                            "case_name": case_name,
                            "deposition": deposition,
                            "summary": summary,
                            "pair_id": f"{case_name}_{deposition}_{summary}"
                        })
        
        pairs.sort(key=lambda x: x['case_name'])
        return JSONResponse(content={"status": "success", "pairs": pairs})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing file pairs: {str(e)}")




@app.post("/api/process-deposition")
async def process_deposition(request: ProcessDepositionRequest):
    logs = []
    try:
        case_name = request.case_name
        deposition_filename = request.deposition_filename
        deposition_path = BASE_DIR / case_name / deposition_filename
        # nuggets_path = NUGGETS_DIR / f"{deposition_filename.replace('.txt', '')}_hierarchical.json"
        nuggets_path = NUGGETS_DIR / f"{deposition_filename.replace('.txt', '')}.json" if MODE=="mapping" else NUGGETS_DIR / f"{deposition_filename.replace('.txt', '')}_hierarchical.json"

        logs.append(f"Processing deposition file: {deposition_path}")
        print("HERE!")
        print(f"Processing deposition: {deposition_path}")  # Debug log
        if not deposition_path.exists():
            logs.append(f"Deposition file not found: {deposition_path}")
            raise HTTPException(status_code=404, detail=f"Deposition file {deposition_filename} not found in case {case_name}")
        
        if nuggets_path.exists():
            logs.append(f"Loading existing nuggets from: {nuggets_path}")
            with open(nuggets_path, 'r', encoding='utf-8') as f:
                nuggets_data = json.load(f)
        
        else:
            logs.append(f"No nuggets found at {nuggets_path}. Generating new nuggets...")
            print("HERE")
            print(len("\n".join(read_transcript_file(str(deposition_path))).split()))

            # print((read_transcript_file(deposition_path)))

            log_pipeline_run(
                deposition_filename,
                "NO SUMMARY",
                len("\n".join(read_transcript_file(str(deposition_path))).split()),
                0,
                step1_run=1,
                step2_run=0,
                # heuristic_cost=round(len(summary_obj.text.split()) * 0.0001, 4),
                CSV_LOG_PATH=CSV_LOG_PATH
            )
            generator = DepositionNuggetGenerator(
                input_path=str(deposition_path),
                output_path=str(nuggets_path)
            )
            generator.run()
            logs.append(f"Nuggets generated successfully at: {nuggets_path}")
            with open(nuggets_path, 'r', encoding='utf-8') as f:
                nuggets_data = json.load(f)
        
        # Transform nuggets data from {nugget0: "text", nugget1: "text"} to [{id: "nugget0", text: "text"}, ...]
        transformed_nuggets = [
            {"id": nugget_id, "text": nugget_info["nugget_text_w_citation"], "citation_str":nugget_info["citation_str"],"link":""}
            for nugget_id, nugget_info in nuggets_data.items()
        ]
        
        print(f"Returning nuggets data: {len(transformed_nuggets)} nuggets")  # Debug log
        return {
            "status": "success",
            "data": {
                "nuggets": transformed_nuggets,
                "nuggets_path": str(nuggets_path)
            },
            "logs": logs
        }
    except Exception as e:
        logs.append(f"FATAL ERROR: {str(e)}")
        print(f"Error in process_deposition: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/get-deposition-text")
async def get_deposition_text(request: GetDepositionRequest):
    """Fetch the raw text of a deposition file."""
    try:
        case_name = request.case_name
        deposition_filename = request.deposition_filename
        deposition_path = BASE_DIR / case_name / deposition_filename
        
        if not deposition_path.exists():
            raise HTTPException(status_code=404, detail=f"Deposition file {deposition_filename} not found in case {case_name}")
        deposition_text = read_transcript_file(deposition_path)
        # with open(deposition_path, 'r', encoding='utf-8') as f:
        #     deposition_text = f.read()
        
        return JSONResponse(content={
            "status": "success",
            "data": {
                "deposition_text": deposition_text
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching deposition text: {str(e)}")


@app.post("/api/process-pair")
async def process_pair(request: ProcessPairRequest = Body(...)):
    """Process a selected deposition and summary file pair for annotation."""
    logs = []
    
    try:
        # Extract parameters from JSON body
        case_name = request.case_name
        deposition_filename = request.deposition_filename
        summary_filename = request.summary_filename
        
        # Construct file paths
        deposition_path = BASE_DIR / case_name / deposition_filename
        summary_path = BASE_DIR / case_name / "summaries" / summary_filename
        
        if not deposition_path.exists():
            raise HTTPException(status_code=404, detail=f"Deposition file {deposition_filename} not found in case {case_name}")
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"Summary file {summary_filename} not found in case {case_name}/summaries")
        
        logs.append(f"Processing deposition file: {deposition_path}")
        logs.append(f"Processing summary file: {summary_path}")
        
        # Initialize summary and citation linking
        summary_obj = Summary(summary_path=str(summary_path))
        deposition_processor = DepositionProcessor(deposition_path=str(deposition_path))
        linker = CitationLinker(summary_obj, deposition_processor)
        
        sorted_citation_data, citation_data = linker.link_citations_to_transcript(include_uncited=True)
        transformed_citation_data = [
            {
                "id": item.get("citation_id") or f"segment-{index}",
                "page": item.get("start_page"),
                "text": item.get("text"),
                "citation_str": item.get("citation_str"),
                "citation_part": item.get("citation_part"),
                "cited": item.get("is_cited"),
                "link": item.get("link"),
                "summary_fact": item.get("summary_fact")
            }
            for index, item in enumerate(sorted_citation_data)
        ]
        transformed_unsorted_citation_data = [
            {
                "id": item.get("citation_id") or f"segment-{index}",
                "page": item.get("start_page"),
                "text": item.get("text"),
                "citation_str": item.get("citation_str"),
                "citation_part": item.get("citation_part"),
                "cited": item.get("is_cited"),
                "link": item.get("link"),
                "summary_fact": item.get("summary_fact")
            }
            for index, item in enumerate(citation_data)
        ]
        
        response_data = {
            "summary": summary_obj.text,
            "stats": {
                "summary_length": len(summary_obj.text.split())
            }
        }
        
        return {
            "status": "success",
            "data": response_data,
            "citation_data": transformed_citation_data,
            "unsorted_citation_data": transformed_unsorted_citation_data,
            "logs": logs,
            "summary_file_name": summary_filename,
            "rand": str(uuid.uuid4()),

        }
    
    except Exception as e:
        logs.append(f"FATAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))





class AnnotationSaveRequest(BaseModel):
    annotations: List[dict]
    resultId: str 

@app.post("/api/save-annotations")
async def save_annotations(data: AnnotationSaveRequest):
    filename = f"annotations_{data.resultId}.json"
    file_path = os.path.join(ANNOTATION_DIR, filename)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data.annotations, f, indent=2)
        return JSONResponse(content={"status": "success", "file": file_path})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/run-pipeline")
async def run_pipeline(
    deposition: UploadFile = File(...),
    summary: UploadFile = File(...),
    human_annotation: bool = Form(False),
    citation_tagging: bool = Form(False),
    nugget_comparison: bool = Form(False)
):
    """Run the pipeline for either evaluation or human annotation"""
    logs = []  # Collect all logs here
    
    # Create temporary directory for uploaded files
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            logs.append(f"Created temporary directory: {temp_dir}")
            
            # Save uploaded files
            deposition_path = Path(temp_dir) / deposition.filename
            summary_path = Path(temp_dir) / summary.filename
            
            with open(deposition_path, "wb") as f:
                shutil.copyfileobj(deposition.file, f)
            with open(summary_path, "wb") as f:
                shutil.copyfileobj(summary.file, f)
            
            logs.append(f"Saved deposition file: {deposition_path}")
            logs.append(f"Saved summary file: {summary_path}")
            
            # Prepare output paths
            deposition_basename = deposition.filename.replace('.txt', '')
            nuggets_path = NUGGETS_DIR / f"{deposition_basename}.json"
            evaluation_path = EVALUATION_DIR / f"{summary.filename}.json"
            
            logs.append(f"Nuggets output path: {nuggets_path}")
            logs.append(f"Evaluation output path: {evaluation_path}")
            
            # Initialize summary and citation linking
            summary_obj = Summary(summary_path=str(summary_path))
            deposition_processor = DepositionProcessor(deposition_path=str(deposition_path))
            linker = CitationLinker(summary_obj, deposition_processor)
            
            sorted_citation_data, citation_data = linker.link_citations_to_transcript(include_uncited=True)
            transformed_citation_data = [
                {
                    "id": item.get("citation_id") or f"segment-{index}",
                    "page": item.get("start_page"),
                    "text": item.get("text"),
                    "citation_str": item.get("citation_str"),
                    "citation_part": item.get("citation_part"),
                    "cited": item.get("is_cited"),
                    "link": item.get("link"),
                    "summary_fact": item.get("summary_fact")
                }
                for index, item in enumerate(sorted_citation_data)
            ]
            transformed_unsorted_citation_data = [
                {
                    "id": item.get("citation_id") or f"segment-{index}",
                    "page": item.get("start_page"),
                    "text": item.get("text"),
                    "citation_str": item.get("citation_str"),
                    "citation_part": item.get("citation_part"),
                    "cited": item.get("is_cited"),
                    "link": item.get("link"),
                    "summary_fact": item.get("summary_fact")

                }
                for index, item in enumerate(citation_data)
            ]
            
            # Prepare response data
            response_data = {
                "summary": summary_obj.text,
                "stats": {
                    "summary_length": len(summary_obj.text.split())
                }
            }
            if human_annotation and citation_tagging and not nugget_comparison:
                # Skip nugget generation and evaluation for human annotation mode
                logs.append("Human annotation mode: Skipping nugget generation and evaluation")
                return {
                    "status": "success",
                    "data": response_data,
                    "nuggets_path": None,
                    "evaluation_path": None,
                    "citation_data": transformed_citation_data,
                    "unsorted_citation_data":transformed_unsorted_citation_data,
                    "logs": logs,
                    "summary_file_name": summary.filename,
                }
            log_pipeline_run(
                deposition.filename,
                summary.filename,
                len("\n".join(read_transcript_file(deposition_path)).split()),
                len(summary_obj.text.split()),
                step1_run=1,
                step2_run=1,
                # heuristic_cost=round(len(summary_obj.text.split()) * 0.0001, 4),
                CSV_LOG_PATH=CSV_LOG_PATH
            )
            # Step 1: Run nugget generation for evaluation mode
            logs.append("=== STARTING NUGGET GENERATION ===")
            nuggets_path = NUGGETS_DIR / f"{deposition_basename}.json"  
                            
            if not nuggets_path.exists():
                logs.append(f"Loading existing nuggets from: {nuggets_path}")

            generator = DepositionNuggetGenerator(
                        input_path=str(deposition_path),
                        output_path=str(nuggets_path))

            generator.run()
            
            
            logs.append("Nugget generation completed successfully")
            
            # Step 2: Run evaluation
            logs.append("=== STARTING EVALUATION ===")
            evaluator = EnhancedSummaryEvaluator()
            evaluation_result = evaluator.evaluate_summary(
                deposition_file_path=str(deposition_path),
                nuggets_file=str(nuggets_path) if MODE=="mapping" else str(nuggets_path).replace(".json", "_hierarchical.json"),
                summary_path=str(summary_path),
                output_path=str(evaluation_path),
                mode="mapping"
            )
            
            logs.append("Evaluation completed successfully")
            
            
            

            return {
                "status": "success",
                "data": {**response_data, **evaluation_result},
                "nuggets_path": str(nuggets_path) if MODE=="mapping" else str(nuggets_path).replace(".json", "_hierarchical.json"),
                "evaluation_path": str(evaluation_path),
                "citation_data": transformed_citation_data,
                "logs": logs
            }
        
        except Exception as e:
            logs.append(f"FATAL ERROR: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))