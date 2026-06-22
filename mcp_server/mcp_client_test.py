"""
MCP protokol testi — smoke_test'ten farkı: fonksiyonu DOĞRUDAN değil,
gerçek MCP protokolü üzerinden (tool listeleme + tool çağırma) test eder.
FastMCP'nin in-memory Client'ı server'ı ayrı process başlatmadan bağlar.

Çalıştırma:  python mcp_server/mcp_client_test.py
"""
import asyncio

from fastmcp import Client

from server import mcp


async def main():
    async with Client(mcp) as client:
        # 1) Client server'a hangi tool'ları görüyor? (tools/list)
        tools = await client.list_tools()
        print("=== Görünen tool'lar ===")
        for t in tools:
            print(f"- {t.name}")
            print(f"  açıklama: {t.description.strip().splitlines()[0]}")
            print(f"  şema: {t.inputSchema}")

        # 2) Tool'u protokol üzerinden çağır (tools/call)
        print("\n=== search_documents çağrısı ===")
        result = await client.call_tool("search_documents", {"query": "graph Laplacian"})
        print(result.content[0].text[:600])


if __name__ == "__main__":
    asyncio.run(main())
