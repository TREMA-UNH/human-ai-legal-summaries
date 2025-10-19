# NextPoint - Legal Summary Analysis

The repository provides tools for transcript processing, nugget extraction, citation linking, and automated evaluation of legal summaries.







https://github.com/user-attachments/assets/c22077f4-5583-44db-9fc6-551e129c9ee2


## Overview

- **Extracting key information nuggets** from depositions using AI
- **Linking citations** between summaries and transcripts
- **Generating structured Q&A pairs** with speaker attribution
- **Evaluating summary quality** against extracted nuggets
- **Providing a web interface** for annotation and review

### Key Features

- **AI-Powered Analysis**: Uses AWS Bedrock (Claude 3.5 Sonnet) for natural language processing
- **Citation Linking**: Automatically links summary statements to transcript locations
- **Quality Evaluation**: Scores summaries based on completeness and accuracy
- **Web Interface**: React-based UI for annotation and review

## Architecture

The platform consists of several interconnected components:

```
NextPoint Platform
├── Core Python Modules (src/)
│   ├── transcript_analysis/     # Q&A extraction and topic modeling
│   ├── vanilla_nugget_generation/   # Key information (nugget) extraction
│   ├── vanilla_nuggetbased_evaluation/  # Summary quality evaluation
│   ├── citation_retriever/     # Citation linking
│   └── llm_conv_segmentation/  # Conversation segmentation -- This is a time consuming approach built before
|                                                               the nugget generation and evaluator
├── Web Interface (deposition-pipeline-ui_/)
│   ├── React frontend with Tailwind CSS
│   └── FastAPI backend (backend/)
└── Data Processing Pipeline
    ├── Input: Raw deposition transcripts
    ├── Processing: AI analysis and extraction
    └── Output: Structured JSON data
```

## Installation

### Prerequisites

- **Python 3.8+**
- **Node.js 16+** (for web interface)
- **AWS Account** with Bedrock access
- **AWS CLI** configured with SSO

### Python Environment Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd nextpoint
```

2. **Install Python dependencies:**
```bash
pip install -e .
```

3. **Install additional dependencies:**
```bash
pip install boto3 botocore pydantic tenacity spacy fastapi uvicorn
python -m spacy download en_core_web_sm (This only was mandatory in the previous versions of the repository)
```

### AWS Configuration

1. **Configure AWS SSO:**
```bash
aws sso login --profile your-profile-name
```

2. **Set environment variables:**
```bash
export AWS_REGION=your-aws-region
export SSO_PROFILE=your-profile-name
export MODEL_PATH=your-llm-of-choice (e.g., anthropic.claude-3-5-sonnet-20240620-v1:0)
```

### Web Interface Setup

1. **Navigate to UI directory:**
```bash
cd deposition-pipeline-ui_
```

2. **Install Node.js dependencies:**
```bash
npm install
```


## Quick Start for using each module seperately and not with the UI


### 1. Extract Key Nuggets

```bash
python -m vanilla_nugget_generation.main \
  --input "path/to/deposition.txt" \
  -o "nuggets.json" \
  --sso-profile your-aws-profile
```

### 2. Evaluate Summary Quality

```bash
python -m vanilla_nuggetbased_evaluation.main \
  --nuggets "nuggets_hierarchical.json" \
  --summary "path/to/summary.txt" \
  --deposition "path/to/deposition.txt" \
  --output "evaluation.json"
```

## Quick start if you just want to run the pipeline through UI:
### Start Web Interface
```bash
aws sso login --profile your-aws-profile
```

```bash
# Start backend API

python -m uvicorn backend.nugget_gen_eval:app --reload --port 8000

# Start frontend (in another terminal)
cd deposition-pipeline-ui_
npm run dev
```

## Core Modules

### 1. Transcript Analysis (`transcript_analysis/`)

Processes legal deposition transcripts to extract structured Q&A pairs and perform topic modeling.

**Key Components:**
- `qa_fact_generation/`: Extracts Q&A pairs with speaker attribution
- `qa_fact_generation_chunk/`: Chunked processing for large documents
- `topic_modeling.py`: FAISS-based topic clustering (a part of the research but not used anymore)
- `faiss_kmeans_topic_modeling.py`: K-means clustering for topics (a part of the research but not used anymore)

**Usage:**
```bash
python -m transcript_analysis.qa_fact_extraction.main \
  -o output.jsonl.gz \
  --input transcript.txt \
  --context-length 2 \
  --max-tokens 5000
```

**Features:**
- Speaker detection and attribution
- Narrative sentence generation
- Configurable context windows
- Batch processing support

### 2. Nugget Generation (`vanilla_nugget_generation/`)

Extracts key information "nuggets" from deposition transcripts using LLM analysis.

**Key Features:**
- Hierarchical nugget organization
- Importance scoring
- Category classification (liability, damages, causation)
- AWS Bedrock integration

**Usage:**
```bash
python -m vanilla_nugget_generation.main \
  --input deposition.txt \
  --output nuggets.json \
  --total-usage \
  --sso-profile your-profile
```

**Output Structure:**
```json
{
  "consolidated_nuggets": [
    {
      "consolidated_id": "C0",
      "text": "..."
    },
    {
      "consolidated_id": "C1",
      "text": "..."
    }
  ],
  "mapping": {
    "C0": [
      {
        "nugget_id": "nugget0",
        "text": "..."
      },
      {
        "nugget_id": "nugget2",
        "text": "..."
      }
    ],
    "C1": [
      {
        "nugget_id": "nugget1",
        "text": "..."
      },
      
    ]
  }
}
```

### 3. Citation Retriever (`citation_retriever/`)

Links citations from legal summaries back to their corresponding locations in deposition transcripts.

**Key Components:**
- `CitationLinker`: Main linking logic
- `DepositionProcessor`: Transcript processing
- `Summary`: Summary parsing and analysis

**Usage:**
```bash
python -m citation_retriever.main \
  --input-deposition deposition.txt \
  --input-summary summary.txt
```

**Features:**
- Automatic citation detection
- Page and line number mapping
- Support for various citation formats

### 4. Summary Evaluation (`vanilla_nuggetbased_evaluation/`)

Evaluates summary quality by comparing against extracted nuggets using multiple criteria.

**Evaluation Metrics:**
- **Completeness**: Coverage of key nuggets
- **Accuracy**: Factual correctness against nuggets
- **Clarity**: Clarity of the summary
- **Citation Quality**: Relevance and sufficicency

**Usage:**
```bash
python -m vanilla_nuggetbased_evaluation.main \
  --nuggets nuggets_hierarchical.json \
  --summary summary.txt \
  --deposition deposition.txt \
  --output evaluation.json \
  --mode mapping (mode can be consolidated or mapping)
```

**Output Structure:**
```json
{
  "summary_path": "/...",
  "summary": "....",
  "criteria_scores": {
    "completeness": {
      "score": 54.166666666666664,
      "explanation": "...",
      "details": [
        {
          "nugget": "...",
          "presence_score": "2, Nugget fully present in summary",
          "explanation": "explanation for the score"
        },
        {
          "nugget": "..",
          "presence_score": "1, Nugget partially mentioned in summary",
          "explanation": "explanation for the score"
        }
      ]
    },
    "accuracy": {
      "has_inaccuracy": false,
      "score": 100.0,
      "explanation": "Expolanation of any conflicts and discrepency between summary and nuggets."
    },
    "structure": {
      "score": [
        {
          "structured": true
        },
        {
          "logical flow": true
        }
      ],
      "explanation": ".."
    },
    "citation_analysis": {
      "score": 76.0,
      "explanation": "Analyzed #n citations",
      "details": [
        {
          "summary_text": "one summary fact with citation",
          "deposition_text": "supporting text in the deposition",
          "accuracy": "YES",
          "evidence_quote": "Evidence for accuracy.",
          "coverage": "COVERED",
          "missing_elements": "null",
          "sufficiency": "SUFFICIENT",
          "sufficiency_reason": "..."
        }
      ]
    }
  },
  "stats": {
    "total_consolidated_nuggets": 14,
    "total_original_nuggets": 24,
    "summary_length": 341
  }
}
```



## Web Interface

The NextPoint web interface provides an intuitive way to process depositions and review results.

### Features

- **File Upload**: Upload deposition and summary files
- **Citation Review**: Interactive citation linking interface
- **Annotation Tools**: Manual annotation and correction
- **Results Export**: Download processed data

### Technology Stack

- **Frontend**: React 19, Tailwind CSS, Vite
- **Backend**: FastAPI, Python
- **UI Components**: Lucide React icons
- **Styling**: Tailwind CSS with PostCSS

### API Endpoints

#### File Management
- `GET /api/file-pairs` - List available deposition/summary pairs
- `POST /api/process-pair` - Process a selected file pair

#### Processing
- `POST /api/run-pipeline` - Run full analysis pipeline
- `POST /api/save-annotations` - Save manual annotations

#### Static Files
- `/annotations/*` - Access annotation files

## Data Models

### Core Data Structures

#### Fact Object
```python
{
  "question": "What happened on the day of the incident?",
  "answer": "I was driving to work when...",
  "question_sa": "MR. Lind: What happened on the day of the incident?",
  "answer_sa": "John Doe: I was driving to work when...",
  "sentence": "John Doe testified that they were driving to work when the incident occurred." or None,
  "conversation": {"Q_SPEAKER": "MR. Lind", "A_SPEAKER": "John Doe"},
  "page_number": 15,
  "line_number": 342,
  "topic": "incident_details",
  "other_info": {}
}
```


#### Citation Object
```python
{
  "citation_id": "cite_001",
  "citation_str": "15:10-16",
  "start_page": 15,
  "end_page": 15,
  "start_line": 10,
  "end_line": 16,
  "text": "Relevant transcript text",
  "is_cited": true,
  "summary_fact": "Corresponding summary statement"
}
```

## Configuration

### Global Configuration (`src/config.py`)

```python
class AppConfig(BaseModel):
    # AWS settings
    aws_region: str = "us-east-1"
    model_path: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    sso_profile: str = "your-profile"
    
    # Processing parameters
    context_length: int = 2
    window_length_for_ner: int = 8
    max_tokens: int = 5000
    seed: int = 0
    

```
