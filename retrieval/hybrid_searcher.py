"""
Hybrid search: Qdrant (vector) + Neo4j (graph) paralel çalışır,
sonuçlar birleştirilir, BGE reranker top-5 seçer.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from retrieval.searcher import search as vector_search
from retrieval.graph_searcher import graph_search
from retrieval.reranker import rerank

logger = logging.getLogger(__name__)

VECTOR_TOP_K = 7   # Qdrant'tan al
GRAPH_TOP_K = 5    # Neo4j'den al  (overlap olabilir, reranker düzeltir)
FINAL_TOP_K = 5    # Reranker'dan çıkan


def hybrid_search(query: str) -> list[dict]:
    """Vektör + graph paralel arama, rerank ile top-5 döner."""

    with ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(vector_search, query, VECTOR_TOP_K)
        graph_future = executor.submit(graph_search, query)
        vector_chunks = vector_future.result()
        graph_chunks = graph_future.result()

    # Birleştir, text'e göre deduplicate
    seen_texts = set()
    merged = []
    for chunk in vector_chunks + graph_chunks:
        key = chunk["text"][:100]
        if key not in seen_texts:
            seen_texts.add(key)
            merged.append(chunk)

    logger.info(f"Hybrid merge: {len(vector_chunks)} vector + {len(graph_chunks)} graph → {len(merged)} unique")

    return rerank(query, merged, top_k=FINAL_TOP_K)
