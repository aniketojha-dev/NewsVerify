from pydantic import BaseModel
from typing import Optional, List, Dict


class QueryRequest(BaseModel):
    query: str


class KeyDetail(BaseModel):
    label: str
    value: str


class QueryResponse(BaseModel):
    answer: str
    short_answer: Optional[str] = None
    key_details: List[KeyDetail] = []
    confidence: Optional[str] = None
    confidence_score: Optional[int] = None
    verification_status: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    year: Optional[int] = None
    sources: List[str] = []
    related_topics: List[str] = []
    error: Optional[str] = None
    evidence: Optional[str] = None
    source_references: List[str] = []
    why_this_result: List[str] = []
    similarity_score: Optional[int] = None
    title: Optional[str] = None
