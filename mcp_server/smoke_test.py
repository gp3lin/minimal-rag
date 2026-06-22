"""
Hızlı smoke test — MCP protokolünü atlayıp search_documents fonksiyonunu
doğrudan çağırır. Amaç: embedding + Qdrant zincirinin çalıştığını görmek.

Çalıştırma:  python mcp_server/smoke_test.py "arama sorusu"
"""
import sys

from server import search_documents

query = sys.argv[1] if len(sys.argv) > 1 else "test"
print(f"Query: {query}\n" + "=" * 60)
print(search_documents(query))
