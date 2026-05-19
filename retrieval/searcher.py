import logging
import os
import httpx
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EMBED_SERVICE_URL = os.getenv("EMBED_SERVICE_URL", "http://localhost:8001")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "math_papers")
TOP_K = int(os.getenv("TOP_K", 5))


def _embed_query(text: str) -> list[float]:
    response = httpx.post(
        f"{EMBED_SERVICE_URL}/embed",
        json={"text": text},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def search(question: str, top_k: int | None = None) -> list[dict]:
    limit = top_k if top_k is not None else TOP_K
    logger.info(f"Arama başlıyor: '{question}'")

    query_vector = _embed_query(question)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    results = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=limit,
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
