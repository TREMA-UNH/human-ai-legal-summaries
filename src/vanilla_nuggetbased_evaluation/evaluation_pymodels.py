"""Pydantic models for structured output evaluation."""

from dataclasses import dataclass
from typing import Any, List, Dict, Optional
from pydantic import BaseModel, Field, root_validator, validator, field_serializer
from statistics import mean







# ----------------------------
# Consolidated Nugget Data
# ----------------------------

class ConsolidatedNuggetItem(BaseModel):
    consolidated_id: str
    text: str
    
    def __getitem__(self, key):
        return getattr(self, key)


class MappedNugget(BaseModel):
    nugget_id: str
    text: str

    def __getitem__(self, key):
        return getattr(self, key)


class NuggetMapping(BaseModel):
    mapping: Dict[str, List[MappedNugget]]

    def __getitem__(self, key):
        return getattr(self, key)
    


class Nugget(BaseModel):
    nugget: str
    from_page: int
    from_line: int
    to_page: int
    to_line: int
    
    
    def __str__(self) -> str:
        return f"{self.nugget} ({self.from_page}:{self.from_line}-{self.to_page}:{self.to_line})"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "nugget_text_w_citation": f"{self.nugget} ({self.from_page}:{self.from_line}-{self.to_page}:{self.to_line})",
            "nugget_text": self.nugget,
            "from_page": self.from_page,
            "from_line": self.from_line,
            "to_page": self.to_page,
            "to_line": self.to_line,
            "citation_str": f"{self.from_page}:{self.from_line}-{self.to_page}:{self.to_line}"
        }

class NuggetsList(BaseModel):
    nuggets: List[Nugget]
    
    def __str__(self) -> str:
        if not self.nuggets:
            return "No nuggets extracted"
        
        result = f"Extracted {len(self.nuggets)} nugget(s):\n"
        for i, nugget in enumerate(self.nuggets, 1):
            result += f"{i}. {nugget}\n"
        return result.rstrip()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "nuggets": [nugget.to_dict() for nugget in self.nuggets]
        }
    
    def to_list(self) -> List[dict]:
        """Convert to list of dictionaries for JSON serialization."""
        return [nugget.to_dict() for nugget in self.nuggets]
    
class NuggetData(BaseModel):
    consolidated_nuggets: List[ConsolidatedNuggetItem]
    mapping: Dict[str, List[MappedNugget]]
    raw_data: Optional[Dict[str, Any]]=None  # Store original if needed

    def __getitem__(self, key):
        return getattr(self, key)

class ConsolidatedNuggetsTemp(BaseModel): # for llm output only, later will add ids to consolidated_nuggets (look NuggetData)
    consolidated_nuggets: List[str]
    mapping: Dict[str, List[str]]  # Maps consolidated nugget text to original nugget IDs

    def __getitem__(self, key):
        return getattr(self, key)

# ----------------------------
# Nugget Coverage (Binary)
# ----------------------------

class NuggetCoverageItem(BaseModel):
    consolidated_id: Optional[str] = None
    text: str
    present: int = -1  # 0 or 1
    explanation: str


class NuggetCoverage(BaseModel):
    c_nuggets: List[NuggetCoverageItem]
    
    @property
    def CTC_score(self) -> float:
        valid_scores = [n.present for n in self.c_nuggets if n.present in (0, 1)]
        return mean(valid_scores) if valid_scores else -1
    
    @field_serializer("CTC_score", when_used="always", check_fields=False)
    def serialize_ctc(self, _):
        return self.CTC_score

# ----------------------------
# Detail Coverage (0–2 scale)
# ----------------------------

class DetailCoverageItem(BaseModel):
    nugget_id: Optional[str] = None
    text: str
    score: int
    explanation: str
    consolidated_id: Optional[str] = None

    @validator("score")
    def score_must_be_valid(cls, v):
        if v not in (0, 1, 2):
            raise ValueError("Score must be 0, 1, or 2")
        return v


class DetailCoverage(BaseModel):
    nuggets: List[DetailCoverageItem]
    consolidated_averages: Dict[str, float] = {}
    overall_average: float = 0.0

    @root_validator(pre=False, skip_on_failure=True)
    def compute_averages(cls, values):
        consolidated_scores = {}
        for nugget in values.get("nuggets", []):
            cid = nugget.consolidated_id or "unknown"
            consolidated_scores.setdefault(cid, []).append(nugget.score)

        values["consolidated_averages"] = {
            cid: mean(scores) for cid, scores in consolidated_scores.items()
        }
        all_scores = [n.score for n in values["nuggets"]]
        values["overall_average"] = mean(all_scores) if all_scores else 0.0
        return values


# ----------------------------
# Criteria Evaluation objs
# ----------------------------


class CompletenessEvaluation(BaseModel):
    presence_score: int = Field(..., enum=[0, 1, 2], description="A score for a supper nugget presence")
    explanation: str = Field(..., description="Explanation of what is missing")
    def __getitem__(self, key):
            return getattr(self, key)



class AccuracyEvaluation(BaseModel):
    has_inaccuracy: bool
    explanation: str

class ConcisenessEvaluation(BaseModel):
    conciseness_score: float 
    redundant_content: bool
    explanation: str

    def __getitem__(self, key):
        return getattr(self, key)


class StructureEvaluation(BaseModel):
    logical_flow:str = Field(..., enum=["Yes","No"])
    format_compliance:str = Field(..., enum=["Yes","No"])
    issues:str

class ClarityEvaluation(BaseModel):
    unclear_count: int
    explanation: str
    def __getitem__(self, key):
        return getattr(self, key)


class CitationEvaluation(BaseModel):
    accuracy:str = Field(..., enum = ["YES", "NO", "PARTIALLY"])
    evidence_quote: str
    coverage: str = Field(..., enum = ["COVERED","NOT COVERED"])
    missing_elements: str
    sufficiency: str = Field(..., enum = ["SUFFICIENT", "INSUFFICIENT"])
    sufficiency_reason: str




class GenQuestion(BaseModel):
    question: str
    type:str =  Field(..., enum=["Yes/No", "Specific Value", "Verification"])
    related_facts: Optional[List[str]]
    
class GenQuestions(BaseModel):
    questions: List[GenQuestion]

# ----------------------------
# Schema Registry
# ----------------------------

EVALUATION_MODELS = {
    "nugget_coverage": NuggetCoverage,
    "detail_coverage": DetailCoverage,
}


def get_model_for_schema(schema_name: str) -> BaseModel:
    return EVALUATION_MODELS[schema_name]
