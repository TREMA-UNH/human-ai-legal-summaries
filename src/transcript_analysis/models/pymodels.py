from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class Conversation(BaseModel):
    Q_SPEAKER: str = Field(default="")
    A_SPEAKER: str = Field(default="")

    def __str__(self):
        return f"Q Speaker: {self.Q_SPEAKER} " f"A Speaker: {self.A_SPEAKER} "


class Fact(BaseModel):
    question: str
    answer: str
    question_sa: str = None  # question with speaker added
    answer_sa: str = None  # answer with speaker added
    sentence: str = None
    topic: Optional[str] = None
    other_info: Optional[str] = None
    conversation: Optional["Conversation"] = None
    page_number: int
    line_number: int

    def __str__(self):
        return f"""
        question: {self.question}
        answer: {self.answer}
        sentence: {self.sentence}
        topic: {self.topic}
        other_info: {self.other_info}
        """


class Sentence(BaseModel):
    sentence: str

    def __str__(self):
        return f"Sentence: {self.sentence}"



class SentenceList(BaseModel):
    results: List[Sentence]




class TopicModelingResult(BaseModel):
    topic: str  # may change later to cover more info




class FactAnnotation(BaseModel):
    segment_id: Optional[int] = None
    segment_topic : Optional[str] = None
    reasoning : Optional[str] = None

    # confidence: Optional[float] = None

    # gray_area: Optional[bool] = None
    # boundary: Optional[bool] = None


class AnnotatedFact(BaseModel):
    fact: Fact
    annotation: FactAnnotation


class FactAnnotationList(BaseModel):
    fact_annotations: List[FactAnnotation]




