import json
import os
import httpx
import numpy as np
import redis.asyncio as aioredis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", 0.90))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 86400))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


async def _embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def get_cached(question: str) -> dict | None:
    """Soruya semantik olarak benzer bir cache kaydı varsa döner."""
    embedding = await _embed(question)
    keys = await redis_client.keys("cache:*")

    for key in keys:
        raw = await redis_client.get(key)
        if not raw:
            continue
        entry = json.loads(raw)
        similarity = _cosine_similarity(embedding, entry["embedding"])
        if similarity >= CACHE_SIMILARITY_THRESHOLD:
            return {"answer": entry["answer"], "citations": entry["citations"], "cache_hit": True}

    return None


async def set_cache(question: str, answer: str, citations: list[dict]) -> None:
    """Soru-cevap çiftini embedding ile birlikte Redis'e yazar."""
    embedding = await _embed(question)
    key = f"cache:{hash(question)}"
    entry = json.dumps({"embedding": embedding, "answer": answer, "citations": citations})
    await redis_client.setex(key, CACHE_TTL_SECONDS, entry)
