import os
import time
import uuid
import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.schemas import ChatRequest, ChatResponse, Citation
from retrieval.searcher import search
from db.database import get_db
from db.models import Conversation, Message
from cache.semantic_cache import get_cached, set_cache

logger = structlog.get_logger()
router = APIRouter()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")
HISTORY_LIMIT = 10

PROMPT_TEMPLATE = """Sen bir matematik asistanısın.
Aşağıdaki bağlamı kullanarak soruyu cevapla.
Bağlamda cevap yoksa "Bu bilgi belgelerimde yer almıyor." de.
Cevabında hangi kaynaktan aldığını belirt.

Bağlam:
{context}

Soru: {question}"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(httpx.HTTPError),
)
async def _call_llm(prompt: str, history: list[dict]) -> str:
    messages = history + [{"role": "user", "content": prompt}]
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": LLM_MODEL, "messages": messages, "stream": False},
        )
        response.raise_for_status()
    return response.json()["message"]["content"]


async def _get_history(conversation_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def _save_messages(conversation_id: str, question: str, answer: str, db: AsyncSession) -> None:
    db.add(Message(conversation_id=conversation_id, role="user", content=question))
    db.add(Message(conversation_id=conversation_id, role="assistant", content=answer))
    await db.commit()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    start = time.time()
    log = logger.bind(question=request.message, conversation_id=request.conversation_id)

    # Semantic cache kontrolü
    cached = await get_cached(request.message)
    if cached:
        latency_ms = round((time.time() - start) * 1000, 2)
        log.info("cache_hit", latency_ms=latency_ms)
        return ChatResponse(
            answer=cached["answer"],
            citations=[Citation(**c) for c in cached["citations"]],
            latency_ms=latency_ms,
            cache_hit=True,
        )

    # Conversation oluştur veya mevcut olanı kullan
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        db.add(Conversation(id=conversation_id))
        await db.commit()

    history = await _get_history(conversation_id, db)

    # Retrieval
    chunks = search(request.message)
    if not chunks:
        raise HTTPException(status_code=404, detail="İlgili chunk bulunamadı")

    context = "\n\n".join(c["text"] for c in chunks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=request.message)

    # LLM (retry ile)
    log.info("llm_request", model=LLM_MODEL, history_length=len(history))
    answer = await _call_llm(prompt, history)

    # Geçmişe kaydet
    await _save_messages(conversation_id, request.message, answer, db)

    citations = [Citation(source=c["source"], page=c["page"], score=c["score"], text=c["text"]) for c in chunks]

    # Cache'e yaz
    await set_cache(request.message, answer, [c.model_dump() for c in citations])

    latency_ms = round((time.time() - start) * 1000, 2)
    log.info("response_sent", latency_ms=latency_ms, cache_hit=False)

    return ChatResponse(
        answer=answer,
        citations=citations,
        latency_ms=latency_ms,
        cache_hit=False,
        conversation_id=conversation_id,
    )
