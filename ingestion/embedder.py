import hashlib
import logging
import os
import pickle
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EMBED_SERVICE_URL = os.getenv("EMBED_SERVICE_URL", "http://localhost:8001")
BATCH_SIZE = 10
CACHE_FILE = Path(__file__).parent / "embeddings_cache.pkl"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "rb") as f:
            cache = pickle.load(f)
        logger.info(f"Embedding cache yüklendi: {len(cache)} kayıt ({CACHE_FILE})")
        return cache
    return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _embed_text(text: str) -> list[float]:
    response = httpx.post(
        f"{EMBED_SERVICE_URL}/embed",
        json={"text": text},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def embed_chunks(chunks: list[dict]) -> list[dict]:
    cache = _load_cache()
    embedded = []
    new_count = 0

    for i, chunk in enumerate(chunks):
        key = _text_hash(chunk["text"])

        if key in cache:
            embedding = cache[key]
        else:
            if new_count == 0 or i % BATCH_SIZE == 0:
                logger.info(f"Embedding: chunk {i + 1}/{len(chunks)}")
            embedding = _embed_text(chunk["text"])
            cache[key] = embedding
            new_count += 1

            # Her 10 yeni embedding'de cache'i diske yaz
            if new_count % BATCH_SIZE == 0:
                _save_cache(cache)

        embedded.append({**chunk, "embedding": embedding})

    if new_count > 0:
        _save_cache(cache)
        logger.info(f"Embedding tamamlandı: {len(embedded)} chunk ({new_count} yeni, {len(embedded) - new_count} cache'den)")
    else:
        logger.info(f"Embedding tamamlandı: {len(embedded)} chunk (tümü cache'den)")

    return embedded
