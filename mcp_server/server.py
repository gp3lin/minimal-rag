"""
Minimal MCP server (Faz 1) — Qdrant tabanlı RAG için tek tool.

Transport: stdio
Tool: search_documents(query) — query'yi embedding mikroservisine gönderir,
dönen vektörle Qdrant'ta arama yapar, bulunan chunk'ları string olarak döndürür.

Çalıştırma:
    Inspector ile:   fastmcp dev mcp_server/server.py
    Doğrudan:        python mcp_server/server.py

Gereken servisler ayakta olmalı:
    - Qdrant            (localhost:6333)
    - Embedding servisi (localhost:8001  ->  embedding_service/serve_app.py)
"""
import os

import httpx
from fastmcp import FastMCP
from qdrant_client import QdrantClient

# --- Bağlantı ayarları (searcher.py ile aynı; env ile override edilebilir) ---
EMBED_SERVICE_URL = os.getenv("EMBED_SERVICE_URL", "http://localhost:8001")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "math_papers")
TOP_K = int(os.getenv("TOP_K", 5))

mcp = FastMCP("rag-search")


def _embed_query(text: str) -> list[float]:
    """Query metnini embedding mikroservisine gönderip 384-dim vektörü alır."""
    response = httpx.post(
        f"{EMBED_SERVICE_URL}/embed",
        json={"text": text},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["embedding"]


@mcp.tool
def search_documents(query: str) -> str:
    """Kullanıcının indekslenmiş akademik PDF koleksiyonunda (matematik makaleleri)
    anlamsal arama yapar ve en alakalı metin parçalarını döndürür.

    Bu tool'u, sorunun cevabı kullanıcının kendi belge koleksiyonundaki bilgiye
    dayandığında kullan: makalelerin içeriği, tanımlar, teoremler, ispatlar,
    yöntemler veya belgelerde geçen herhangi bir özel bilgi. Genel dünya bilgisi
    için (örn. "Python nedir") bu tool'u kullanma.

    Args:
        query: Doğal dildeki arama sorusu (kullanıcının sorusuyla aynı dilde olabilir).

    Returns:
        Bulunan her parça için kaynak dosya, sayfa, benzerlik skoru ve metni içeren
        okunabilir bir string. Sonuç bulunmazsa bunu belirten bir mesaj döner.
    """
    try:
        query_vector = _embed_query(query)
    except Exception as e:
        return f"Embedding servisine ulaşılamadı ({EMBED_SERVICE_URL}): {e}"

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=TOP_K,
        )
    except Exception as e:
        return f"Qdrant'a ulaşılamadı ({QDRANT_HOST}:{QDRANT_PORT}): {e}"

    if not results:
        return f"'{query}' için koleksiyonda ('{QDRANT_COLLECTION}') alakalı bir sonuç bulunamadı."

    parts = []
    for i, hit in enumerate(results, start=1):
        source = hit.payload.get("filename", "?")
        page = hit.payload.get("page", "?")
        text = hit.payload.get("text", "")
        parts.append(
            f"[{i}] kaynak: {source} (sayfa {page}) | skor: {round(hit.score, 4)}\n{text}"
        )

    return "\n\n".join(parts)


if __name__ == "__main__":
    mcp.run()
