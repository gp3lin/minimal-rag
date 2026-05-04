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

## Proje 3 — Agentic RAG `🔒`

**Hedef:** Agent'ın nasıl "düşündüğünü" anlamak.

**Eklenecekler:** LangGraph · Query rewriting · HyDE · Tool use (calculator, web search)

**Ne yapılacak:**
- Planner / Retriever / Responder node'ları
- Self-RAG döngüsü: cevap yeterli değilse tekrar ara
- Basit sorularda retrieval yerine direkt araç kullan

**Kazanımlar:** LangGraph'ın state machine mantığı, agent'ın neden bazen döngüye girdiği, tool kullanımının ne zaman retrieval'dan daha iyi olduğu.

---

## Proje 4 — Hybrid Retrieval + Knowledge Graph `🔒`

**Hedef:** Vektörün yetersiz kaldığı yerde graph'ın ne kattığını görmek.

**Eklenecekler:** Neo4j · Graph extraction pipeline · Hybrid search · Reranker (BGE)

**Ne yapılacak:**
- Aynı corpus'u hem vektöre hem graph'a yaz
- "X ile Y arasındaki ilişki nedir?" sorularında vektör vs hybrid karşılaştır
- Reranker ekleyip retrieval kalitesinin nasıl değiştiğini ölç

**Kazanımlar:** Knowledge graph'ın gerçekten ne zaman fark yarattığı, reranking'in önemi, hybrid search'ün trade-off'ları.

---

## Proje 5 — Scalable Infrastructure `🔒`

**Hedef:** Sistemi Kubernetes ile deploy etmek.

**Eklenecekler:** Kubernetes (minikube) · Helm · Ray Serve · HPA · Terraform (opsiyonel)

**Ne yapılacak:**
- Proje 3'teki sistemi K8s'e taşı
- Helm ile Qdrant ve Neo4j deploy et
- Ray Serve ile embedding modelini mikroservis yap
- Load test yaz, autoscaling'i gözlemle

**Kazanımlar:** Kubernetes'in neden bu kadar merkezi olduğu, Helm'in ne sorunu çözdüğü, model serving'in API'den neden ayrılması gerektiği.

---

## Genel Bakış

| Proje              | Odak               | Durum          |
|--------------------|--------------------|----------------|
| 1 — Minimal RAG    | RAG özü            | ✅ Tamamlandı  |
| 2 — Production     | Güvenilirlik       | ✅ Tamamlandı  |
| 3 — Agentic        | Akıl yürütme       | ⏳ Sıradaki    |
| 4 — Hybrid         | Retrieval kalitesi | 🔒             |
| 5 — Scale          | Dağıtık sistemler  | 🔒             |
