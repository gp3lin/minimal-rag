import os
import time
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.schemas import ChatRequest, ChatResponse, Citation
from agent.graph import agent
from db.database import get_db
from db.models import Conversation, Message
from cache.semantic_cache import get_cached, set_cache

logger = structlog.get_logger()
router = APIRouter()


async def _get_history(conversation_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(10)
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

    # Agent graph'ı çalıştır
    log.info("agent_start")
    result = await agent.ainvoke({
        "question": request.message,
        "rewritten_query": "",
        "route": "",
        "hyde_document": "",
        "chunks": [],
        "answer": "",
        "is_sufficient": False,
        "retry_count": 0,
        "history": history,
    })

    answer = result["answer"]
    chunks = result.get("chunks", [])

    if not answer:
        raise HTTPException(status_code=500, detail="Agent cevap üretemedi")

    await _save_messages(conversation_id, request.message, answer, db)

    citations = [
        Citation(source=c["source"], page=c["page"], score=c["score"], text=c["text"])
        for c in chunks
    ]

    await set_cache(request.message, answer, [c.model_dump() for c in citations])

    latency_ms = round((time.time() - start) * 1000, 2)
    log.info("agent_done", latency_ms=latency_ms, route=result.get("route"), retry_count=result.get("retry_count"))

    return ChatResponse(
        answer=answer,
        citations=citations,
        latency_ms=latency_ms,
        cache_hit=False,
        conversation_id=conversation_id,
    )
