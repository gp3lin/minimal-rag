import logging
import os
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
BATCH_SIZE = 10


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Her chunk için Ollama'dan embedding alır, 10'ar chunk'lık batch'ler halinde işler."""
    embedded = []

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start: batch_start + BATCH_SIZE]
        logger.info(
            f"Embedding: chunk {batch_start + 1}–{batch_start + len(batch)} / {len(chunks)}"
        )

        for chunk in batch:
            response = httpx.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": chunk["text"]},
                timeout=60.0,
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]

            embedded.append({
                **chunk,
                "embedding": embedding,
            })

    logger.info(f"Embedding tamamlandı: {len(embedded)} chunk")
    return embedded
