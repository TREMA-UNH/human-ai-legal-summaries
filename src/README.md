# NextPoint - Legal Deposition Analysis Platform

NextPoint is a comprehensive Python-based platform for analyzing legal depositions using advanced natural language processing and machine learning techniques. The system provides tools for transcript processing, nugget extraction, citation linking, conversation segmentation, and automated evaluation of legal summaries.

## Overview

This platform is designed to assist legal professionals in analyzing deposition transcripts by:
- Extracting key information nuggets from depositions
- Linking citations between summaries and transcripts
- Segmenting conversations into meaningful topics
- Evaluating summary quality against extracted nuggets
- Generating rubrics for case evaluation

## Architecture

The project is organized into several specialized modules:

### Core Modules

#### 1. Citation Retriever (`citation_retriever/`)
Links citations from legal summaries back to their corresponding locations in deposition transcripts.

**Key Components:**
- `CitationLinker`: Main class for linking citations to transcript locations
- `DepositionProcessor`: Processes raw deposition files
- `Summary`: Parses and analyzes summary documents

**Usage:**
```bash
python -m citation_retriever.main \
  --input-deposition path/to/deposition.txt \
  --input-summary path/to/summary.txt
```

#### 2. Vanilla Nugget Generation (`vanilla_nugget_generation/`)
Extracts key information "nuggets" from deposition transcripts using LLM-based analysis.

**Features:**
- Chunked processing for large documents
- Hierarchical nugget organization
- AWS Bedrock integration for LLM processing

**Usage:**
```bash
python -m vanilla_nugget_generation.main \
  --input path/to/deposition.txt \
  --output path/to/nuggets.json \
  --sso-profile your-aws-profile
```

#### 3. Nugget-Based Evaluation (`vanilla_nuggetbased_evaluation/`)
Evaluates summary quality by comparing against extracted nuggets using various criteria.

**Evaluation Criteria:**
- Completeness: How well the summary covers key nuggets
- Accuracy: Factual correctness of summary content
- Relevance: Alignment with important case elements

**Usage:**
```bash
python -m vanilla_nuggetbased_evaluation.main \
  --nuggets path/to/nuggets.json \
  --summary path/to/summary.txt \
  --deposition path/to/deposition.txt \
  --output path/to/evaluation.json
```

#### 4. LLM Conversation Segmentation (`llm_conv_segmentation/`)
Segments deposition conversations into topical segments with confidence scoring.

**Features:**
- Automatic topic detection
- Confidence level assignment
- Segment boundary identification

**Usage:**
```bash
python -m llm_conv_segmentation.main \
  --input conversation_data.jsonl.gz \
  --output segmented_data.jsonl.gz \
  --sso-profile your-aws-profile
```

#### 5. Transcript Analysis (`transcript_analysis/`)
Provides topic modeling and fact extraction capabilities for transcript analysis.

**Components:**
- Topic modeling using transformer models
- Fact extraction and annotation
- FAISS-based clustering for topic discovery

## Configuration

The system uses a centralized configuration system (`config.py`) with the following key settings:

```python
# AWS Configuration
aws_region = "us-east-1"
model_path = "anthropic.claude-3-5-sonnet-20240620-v1:0"
sso_profile = "your-aws-profile"

# Processing Parameters
context_length = 2
max_tokens = 5000
chunk_size = 5000
```

## Data Models

The system uses Pydantic models for type safety and validation:

### Core Models
- `Fact`: Represents Q&A pairs from depositions with metadata
- `Conversation`: Defines speaker roles and conversation structure
- `AnnotatedFact`: Facts with segmentation and topic annotations
- `TopicModelingResult`: Results from topic classification

### Example Fact Structure
```python
{
  "question": "What happened on the day of the incident?",
  "answer": "I was driving to work when...",
  "sentence": "Combined Q&A text",
  "topic": "incident_details",
  "page_number": 15,
  "line_number": 342
}
```

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd nextpoint
```

2. **Install dependencies:**
```bash
pip install -e .
```

3. **Configure AWS credentials:**
```bash
aws configure sso --profile your-profile-name
```

4. **Set environment variables:**
```bash
export AWS_REGION=us-east-1
export SSO_PROFILE=your-profile-name
```

## Quick Start

### 1. Extract Nuggets from Deposition
```bash
python -m vanilla_nugget_generation.main \
  --input data/deposition.txt \
  --output results/nuggets.json \
  --sso-profile your-aws-profile
```

### 2. Evaluate Summary Quality
```bash
python -m vanilla_nuggetbased_evaluation.main \
  --nuggets results/nuggets.json \
  --summary data/summary.txt \
  --deposition data/deposition.txt \
  --output results/evaluation.json
```

### 3. Link Citations
```bash
python -m citation_retriever.main \
  --input-deposition data/deposition.txt \
  --input-summary data/summary.txt
```

## Advanced Features

### Rubric Generation
Generate evaluation rubrics for different case types:

```bash
python rubric_on_cases_list.py \
  --input cases.csv \
  --output rubrics.jsonl \
  --prompt_idx 4
```

### Batch Processing
Use the evaluation script for batch processing:

```bash
./evaluate.sh
```

## Output Formats

### Nuggets Output
```json
{
  "nuggets": [
    {
      "content": "Key fact or finding",
      "importance": "high",
      "category": "liability",
      "source_pages": [15, 16]
    }
  ],
  "hierarchical_nuggets": {
    "liability": [...],
    "damages": [...],
    "causation": [...]
  }
}
```

### Evaluation Results
```json
{
  "completeness_score": 0.85,
  "accuracy_score": 0.92,
  "overall_score": 0.88,
  "missing_nuggets": [...],
  "evaluation_details": {...}
}
```

## Dependencies

- **Python 3.8+**
- **AWS Bedrock** for LLM processing
- **PyTorch** for model operations
- **Pydantic** for data validation
- **Pandas** for data manipulation
- **FAISS** for similarity search
- **Outlines** for structured generation

## Contributing

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Include docstrings for public methods
4. Write unit tests for new features
5. Update documentation for API changes

## License

This project is proprietary software developed for legal document analysis.

## Support

For technical support or questions about the platform, please contact the development team.

---

**Note:** This platform requires AWS credentials and access to Bedrock services for full functionality. Ensure proper authentication is configured before running analysis tasks.