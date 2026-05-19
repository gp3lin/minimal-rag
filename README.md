# Scalable RAG System

5 projeden oluşan, katman katman ilerleyen bir RAG sistemi öğrenme serisi.
Her proje bir öncekinin üzerine yeni bir katman ekler — sıfırdan başlamaz.

---

## Temel Prensip

```
Proje 1 → RAG'ın özü
Proje 2 → Production kalitesi
Proje 3 → Agentic düşünce
Proje 4 → Hybrid retrieval
Proje 5 → Ölçek ve dağıtık sistemler
```

---

## Proje 1 — Minimal RAG `✅ Tamamlandı`

**Hedef:** Sistemin kalbi nasıl atar?

**Stack:** FastAPI · Qdrant · Ollama (Qwen) · LlamaIndex · Docker Compose

**Ne yapılacak:**
- PDF yükle, chunk'la, embed et, Qdrant'a yaz
- Soru sor → vektör ara → LLM'e ver → cevap al
- RAGAS ile faithfulness ve answer_relevancy ölçümü

**Kazanımlar:** Ingestion pipeline'ının her adımı, embedding'in ne işe yaradığı, retrieval'ın neden bazen başarısız olduğu bizzat görüldü.

---

## Proje 2 — Production Temelleri `✅ Tamamlandı`

**Hedef:** Sistemi güvenilir ve gözlemlenebilir yapmak.

**Stack:** PostgreSQL · Redis · structlog · tenacity

**Ne yapıldı:**
- Multi-turn konuşma (sohbet geçmişi PostgreSQL'de, son 10 mesaj bağlam olarak)
- Semantic cache: cosine similarity ≥ 0.90 ise Redis'ten dön (~150ms vs ~38sn)
- Exponential backoff retry: Ollama hata verirse 3 kez dene
- JSON structured logging: cache_hit, latency_ms, conversation_id her log'da

**Kazanımlar:** Neden production sistemlerde her şey async yazıldığı, semantic cache'in exact match'ten farkı, structured log'un neden önemli olduğu.

---

## Proje 3 — Agentic RAG `✅ Tamamlandı`

**Hedef:** Agent'ın nasıl "düşündüğünü" anlamak.

**Stack:** LangGraph · HyDE · Query rewriting · Self-RAG · Calculator (ast)

**Ne yapıldı:**
- Planner soruyu analiz edip rota seçiyor: retrieval veya calculator
- HyDE ile hayali cevap embed ediliyor → retrieval skoru 0.62'den 0.74'e çıktı
- Self-RAG: evaluator cevap yeterliliğini kontrol ediyor, yetersizse tekrar deniyor
- Calculator: hesap sorularında Qdrant'a gitmiyor, ast ile güvenli eval

**Kazanımlar:** LangGraph'ın state machine mantığı, HyDE'nin retrieval'a etkisi, Self-RAG döngüsünün nasıl çalıştığı.

---

## Proje 4 — Hybrid Retrieval + Knowledge Graph `✅ Tamamlandı`

**Hedef:** Vektörün yetersiz kaldığı yerde graph'ın ne kattığını görmek.

**Stack:** Neo4j · Graph extraction (spaCy) · Hybrid search · BGE Reranker

**Ne yapıldı:**
- Neo4j'e entity+ilişki graph'ı yazıldı (spaCy ile chunk başına max 10 co-occurrence triple)
- Hybrid search: Qdrant (7) + Neo4j (5) paralel → BGE reranker → top-5
- `retriever` node HyDE doc'u artık her iki kaynağa da soruyor
- `rerank_score` field'ı ile chunk kalitesi izlenebilir

**Kazanımlar:** Graph'ın "SVD↔PCA" gibi kavramsal ilişkileri vektörden önce bulması, reranking'in kaynak bağımsız sıralama yapması, hybrid merging'de deduplication önemi.

---

## Proje 5 — Scalable Infrastructure `✅ Tamamlandı`

**Hedef:** Embedding'i bağımsız bir mikroservise taşımak, K8s altyapısını hazırlamak.

**Stack:** FastAPI · sentence-transformers · Kubernetes · Helm · HPA · locust

**Ne yapıldı:**
- Embedding Ollama'dan koparıldı → bağımsız FastAPI mikroservisi (all-MiniLM-L6-v2, 384-dim)
- `embedder.py` ve `searcher.py` yeni servise bağlandı, Ollama sadece LLM için kaldı
- Embedding cache (`embeddings_cache.pkl`) eklendi — script kesilirse sıfırdan başlamaz
- K8s manifest'leri yazıldı: Deployment, Service, HPA (1→4 replica, %50 CPU eşiği)
- locust yük testi hazırlandı (`load_test/locustfile.py`)
- Qdrant koleksiyonu 768-dim → 384-dim otomatik migration eklendi

**Kazanımlar:** Model serving'in API'den neden ayrılması gerektiği, HPA'nın nasıl çalıştığı, Kubernetes manifest yapısı, embedding cache'in önemi.

---

## Genel Bakış

| Proje              | Odak               | Durum          |
|--------------------|--------------------|----------------|
| 1 — Minimal RAG    | RAG özü            | ✅ Tamamlandı  |
| 2 — Production     | Güvenilirlik       | ✅ Tamamlandı  |
| 3 — Agentic        | Akıl yürütme       | ✅ Tamamlandı  |
| 4 — Hybrid         | Retrieval kalitesi | ✅ Tamamlandı  |
| 5 — Scale          | Dağıtık sistemler  | ✅ Tamamlandı  |
