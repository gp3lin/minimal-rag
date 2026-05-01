import logging
import os
import time
import httpx
from fastapi import APIRouter, HTTPException

from api.schemas import ChatRequest, ChatResponse, Citation
from retrieval.searcher import search

logger = logging.getLogger(__name__)

router = APIRouter()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")

PROMPT_TEMPLATE = """Sen bir matematik asistanısın.
Aşağıdaki bağlamı kullanarak soruyu cevapla.
Bağlamda cevap yoksa "Bu bilgi belgelerimde yer almıyor." de.
Cevabında hangi kaynaktan aldığını belirt.

Bağlam:
{context}

Soru: {question}"""


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start = time.time()

    chunks = search(request.message)
    if not chunks:
        raise HTTPException(status_code=404, detail="İlgili chunk bulunamadı")

    context = "\n\n".join(c["text"] for c in chunks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=request.message)

    logger.info(f"LLM'e istek gönderiliyor: {LLM_MODEL}")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        response.raise_for_status()

    answer = response.json()["message"]["content"]
    latency_ms = round((time.time() - start) * 1000, 2)

    citations = [
        Citation(source=c["source"], page=c["page"], score=c["score"], text=c["text"])
        for c in chunks
    ]

    logger.info(f"Cevap üretildi ({latency_ms} ms)")
    return ChatResponse(answer=answer, citations=citations, latency_ms=latency_ms)
