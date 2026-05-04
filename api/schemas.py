from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class Citation(BaseModel):
    source: str
    page: int
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    latency_ms: float
    cache_hit: bool
    conversation_id: Optional[str] = None
