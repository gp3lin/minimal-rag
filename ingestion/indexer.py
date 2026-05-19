import logging
import os
import sys
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from loader import load_pdf
from chunker import chunk_pages
from embedder import embed_chunks
from graph_extractor import build_knowledge_graph

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "math_papers")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", 384))


def get_client() -> QdrantClient:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    logger.info(f"Qdrant bağlantısı kuruldu: {QDRANT_HOST}:{QDRANT_PORT}")
    return client


def ensure_collection(client: QdrantClient) -> None:
    existing = {c.name: c for c in client.get_collections().collections}
    if QDRANT_COLLECTION in existing:
        info = client.get_collection(QDRANT_COLLECTION)
        current_size = info.config.params.vectors.size
        if current_size != VECTOR_SIZE:
            logger.info(f"Collection boyutu uyuşmuyor ({current_size} → {VECTOR_SIZE}), yeniden oluşturuluyor")
            client.delete_collection(QDRANT_COLLECTION)
        else:
            logger.info(f"Collection zaten mevcut: {QDRANT_COLLECTION}")
            return

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    logger.info(f"Collection oluşturuldu: {QDRANT_COLLECTION} (dim={VECTOR_SIZE})")


def upsert_chunks(client: QdrantClient, embedded_chunks: list[dict]) -> None:
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk["embedding"],
            payload={
                "text": chunk["text"],
                **chunk["metadata"],
            },
        )
        for chunk in embedded_chunks
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    logger.info(f"{len(points)} chunk Qdrant'a yazıldı")


def index_pdf(filepath: str, build_graph: bool = True) -> None:
    logger.info(f"İndeksleme başlıyor: {filepath}")

    pages = load_pdf(filepath)
    chunks = chunk_pages(pages)
    embedded = embed_chunks(chunks)

    client = get_client()
    ensure_collection(client)
    upsert_chunks(client, embedded)

    if build_graph:
        logger.info("Knowledge graph oluşturuluyor...")
        build_knowledge_graph(chunks)

    logger.info("İndeksleme tamamlandı")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Kullanım: python ingestion/indexer.py data/papers/paper.pdf")
        sys.exit(1)

    index_pdf(sys.argv[1])
