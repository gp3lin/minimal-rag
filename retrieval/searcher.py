import logging
import os
import httpx
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "math_papers")
TOP_K = int(os.getenv("TOP_K", 5))


def _embed_query(question: str) -> list[float]:
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": question},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def search(question: str) -> list[dict]:
    """Soruyu embed eder, Qdrant'ta arar, top-K chunk'ı döner."""
    logger.info(f"Arama başlıyor: '{question}'")

    query_vector = _embed_query(question)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    results = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=TOP_K,
    )

    chunks = [
        {
            "text": hit.payload["text"],
            "source": hit.payload.get("filename", ""),
            "page": hit.payload.get("page", 0),
            "score": round(hit.score, 4),
        }
        for hit in results
    ]

    logger.info(f"{len(chunks)} chunk bulundu (en yüksek skor: {chunks[0]['score'] if chunks else '-'})")
    return chunks
