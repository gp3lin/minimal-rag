from pydantic import BaseModel
from typing import List


class ChatRequest(BaseModel):
    message: str


class Citation(BaseModel):
    source: str
    page: int
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    latency_ms: float
