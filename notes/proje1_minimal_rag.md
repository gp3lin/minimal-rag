# Proje 1 — Minimal RAG Sistemi

## Amaç

Akademik PDF'ler üzerine soru sorulabilen, tamamen local çalışan minimal bir RAG sistemi.
Öğrenme projesi — sonraki projelerde üzerine katman eklenecek.

---

## Stack

| Bileşen | Teknoloji | Not |
|---|---|---|
| LLM | Ollama + qwen3:4b | Local, ücretsiz |
| Embedding | Ollama + nomic-embed-text | Multilingual, local |
| Vektör DB | Qdrant v1.7.3 | Docker container |
| API | FastAPI + uvicorn | Docker container |
| Ortam | Docker Compose | Servis izolasyonu |

---

## Dosya Yapısı

```
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .env                        # git'e gitmiyor
├── .gitignore
├── requirements.txt            # tüm bağımlılıklar (lokal için)
├── requirements.api.txt        # sadece API bağımlılıkları (Docker için)
│
├── ingestion/
│   ├── loader.py               # PDF → sayfa metinleri
│   ├── chunker.py              # Metin → chunk (512 token, 50 overlap)
│   ├── embedder.py             # Chunk → vektör (Ollama, batch 10)
│   └── indexer.py              # Vektör → Qdrant (CLI ile çalışır)
│
├── retrieval/
│   └── searcher.py             # Soru → embed → Qdrant ara → top-5 chunk
│
├── api/
│   ├── main.py                 # FastAPI uygulaması, lifespan
│   ├── schemas.py              # ChatRequest, Citation, ChatResponse
│   └── routes/
│       └── chat.py             # POST /chat endpoint'i
│
├── eval/
│   ├── golden_dataset.json     # 10 soru (5 TR + 5 EN), ground truth ile
│   └── ragas_eval.py           # RAGAS ölçümü → eval/reports/results.json
│
└── data/
    └── papers/                 # PDF'ler buraya (git'e gitmiyor)
```

---

## Sistem Akışı

### Ingestion (bir kez çalışır)
```
paper.pdf
  → loader.py    → sayfa metinleri + metadata
  → chunker.py   → chunk + chunk_index + MD5 hash
  → embedder.py  → chunk + 768 boyutlu vektör (Ollama'ya HTTP)
  → indexer.py   → Qdrant'a upsert (uuid, vector, payload)
```
```bash
python ingestion/indexer.py data/papers/paper.pdf
```

### Retrieval + API (her sorguda çalışır)
```
POST /chat {"message": "..."}
  → searcher.py: soruyu embed et → Qdrant'ta ara → top-5 chunk
  → chunk metinleri prompt'a doldurulur
  → Ollama /api/chat'e async gönderilir
  → {"answer": "...", "citations": [...], "latency_ms": ...}
```

### Evaluation
```bash
python eval/ragas_eval.py
```
- 10 soruyu API'ye gönderir, cevap + chunk metni alır
- RAGAS ile faithfulness + answer_relevancy ölçer (Ollama backend ile)
- TR vs EN karşılaştırmasını `eval/reports/results.json`'a yazar

---

## Öğrenilen Dersler

**Retrieval kalitesi:**
- Türkçe sorgular EN < 0.55 cosine skoru alıyor (paper İngilizce olduğu için)
- İngilizce sorgular 0.60–0.78 arasında
- İyileştirme yolları: sorgu çevirisi, hybrid search, daha iyi embedding modeli

**Golden dataset tasarımı:**
- Survey makalelerinde temel tanımlar (SVD nedir?) bulunmayabilir
- Sorular corpus'un gerçek içeriğiyle eşleşmeli
- Sistem "cevap yoksa bilmiyorum demeli" — bu doğru davranış, hata değil

**Docker:**
- `requirements.txt` Docker build'de çok ağır olabilir — API için ayrı minimal `requirements.api.txt` kullanıldı
- Healthcheck için `curl` Qdrant container'ında yoktu, `wget` kullanıldı
- `.env` değişikliği sonrası container yeniden başlatılmalı

**RAGAS:**
- Varsayılan olarak OpenAI kullanıyor — local için `langchain-ollama` ile override edilmeli
- `contexts` alanına kaynak adı değil gerçek chunk metni verilmeli

---

## Servisler

| Servis | Nerede | Adres |
|---|---|---|
| Ollama | Host makine | localhost:11434 / host.docker.internal:11434 |
| Qdrant | Docker | localhost:6333 (dış) / qdrant:6333 (Docker içi) |
| API | Docker | localhost:8000 |

---

## Corpus

**Paper:** A Literature Survey of Matrix Methods for Data Science
**Kaynak:** arxiv.org/abs/1912.07896
**Dosya:** data/papers/matrix_methods.pdf
**İstatistik:** 31 sayfa → 228 chunk → 228 × 768 boyutlu vektör
