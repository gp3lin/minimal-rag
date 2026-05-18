# Proje 4 — Hybrid Retrieval + Knowledge Graph

## Hedef
Vektörün yetersiz kaldığı sorularda (kavramlar arası ilişki) graph traversal'ın farkını görmek.

## Yeni Bileşenler

### Neo4j (Knowledge Graph)
- Docker Compose'a eklendi: port 7474 (HTTP), 7687 (Bolt)
- Şema: `(:Entity {name}) -[:RELATED_TO {relation, chunk_text, chunk_id}]-> (:Entity)`
- Ingestion sırasında `graph_extractor.py` çalışır

### Graph Extraction Pipeline (`ingestion/graph_extractor.py`)
- **spaCy** (`en_core_web_sm`) kullanır — LLM çağrısı yok
- Her chunk'tan noun chunk'lar entity olarak çıkarılır
- Aynı chunk'ta birlikte geçen entity çiftleri `co-occurs` ilişkisiyle bağlanır
- Chunk başına max 10 çift, min entity uzunluğu 3 karakter
- 228 chunk için toplam süre: ~5 saniye

#### Neden LLM yerine spaCy?

İlk tasarımda Qwen'e her chunk için "entity ve ilişki çıkar" diye soruyorduk.
Bu yaklaşımla karşılaşılan sorunlar:

| Sorun | Detay |
|---|---|
| Süre (chunk başına) | ~2 dakika (RTX 4050 laptop GPU'sunda bile) |
| Toplam ingestion süresi | ~7-8 saat (228 chunk × LLM çağrısı) |
| Batch denenme | 5 chunk/call → ~90 dk, yine kabul edilemez |

**Karar:** LLM'i graph extraction adımından tamamen çıkar, spaCy ile değiştir.

**Trade-off:**
- LLM → "SVD **decomposes** matrix" (anlamlı ilişki etiketi)
- spaCy → "SVD **co-occurs** matrix" (yüzeysel ama hızlı)

Bu bir öğrenme projesi. Graph'ın sisteme ne kattığını görmek için
ilişki etiketinin mükemmel olması şart değil — "SVD ile PCA aynı
chunk'ta geçiyor" bilgisi graph traversal'ı çalıştırmak için yeterli.

### Graph Searcher (`retrieval/graph_searcher.py`)
- Query'den entity'leri Qwen ile çıkarır
- Neo4j'de `toLower CONTAINS` ile fuzzy eşleşme
- İlgili chunk_text'leri döner

### Hybrid Searcher (`retrieval/hybrid_searcher.py`)
- Qdrant (7 chunk) + Neo4j (5 chunk) paralel (ThreadPoolExecutor)
- Text'in ilk 100 karakterine göre deduplicate
- BGE reranker'a verir

### BGE Reranker (`retrieval/reranker.py`)
- Model: `BAAI/bge-reranker-base` (~400MB, ilk çalıştırmada indirilir)
- Cross-encoder: (query, passage) çifti → skor
- Top-10 → Top-5

### Agent Değişikliği (`agent/nodes.py`)
- `retriever` node: `search()` → `hybrid_search()`
- HyDE doc hem vektör hem graph aramasına girer
- `rerank_score` ile log'lanır

## Çalıştırma Sırası

### 1. Neo4j'i başlat
```bash
docker compose up -d neo4j
```

### 2. Paketleri yükle
```bash
pip install neo4j==5.26.0 sentence-transformers==3.3.1
```

### 3. Graph ingestion (yeni indeksleme — yaklaşık 10-15dk)
```bash
cd ingestion
python indexer.py ../data/papers/paper.pdf
```

### 4. API'yi yeniden başlat
```bash
docker compose up -d --build api
```

### 5. Test
```bash
# Vektörün zayıf olduğu ilişki sorusu:
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the relationship between SVD and PCA?"}'
```

## Beklenen Kazanımlar
- "SVD ile PCA ilişkisi?" → graph traversal direkt bağlantıyı bulur
- Rerank skoru ile chunk kalitesi ölçülebilir
- `graph_context` field'ı hangi entity yolundan geldiğini gösterir

## Notlar
- Graph extraction LLM çağrısı chunk başına ~3sn → 228 chunk ≈ 11dk
- BGE model ilk çalıştırmada HuggingFace'ten indirilir
- Neo4j Browser: http://localhost:7474 (neo4j / ragpassword)
- Ingestion lokalde çalışır (NEO4J_URI=bolt://localhost:7687 gerekir)
