# Proje 2 — Production Temelleri

## Amaç

Proje 1'deki minimal RAG sistemine production kalitesi kazandırmak:
güvenilirlik, gözlemlenebilirlik ve performans.

---

## Eklenen Stack

| Bileşen | Teknoloji | Ne için |
|---|---|---|
| Sohbet geçmişi | PostgreSQL 16 | Multi-turn konuşma |
| Semantic cache | Redis 7 | Tekrar eden sorularda Ollama'ya gitme |
| Retry | tenacity | Ollama geçici hata verirse yeniden dene |
| Structured logging | structlog | JSON formatında filtrelenebilir log |

---

## Yeni Dosyalar

```
├── db/
│   ├── database.py         # Async PostgreSQL bağlantısı (SQLAlchemy)
│   └── models.py           # Conversation + Message tabloları
│
├── cache/
│   └── semantic_cache.py   # Redis'te embedding tabanlı cache
```

---

## Sistem Akışı (Güncel)

```
POST /chat
  → Redis'te semantic cache ara (cosine similarity ≥ 0.90)
    → HIT:  Ollama'ya gitme, direkt cevap dön
    → MISS:
        → conversation_id yoksa yeni UUID üret, PostgreSQL'e kaydet
        → son 10 mesajı PostgreSQL'den çek
        → Qdrant'ta ara, top-5 chunk al
        → prompt oluştur, Ollama'ya gönder (3 deneme, exponential backoff)
        → user + assistant mesajlarını PostgreSQL'e kaydet
        → cevabı Redis'e yaz (TTL: 24 saat)
        → cevap dön
```

---

## Öğrenilen Kavramlar

**Multi-turn konuşma**
Her soru-cevap çifti PostgreSQL'e kaydediliyor. Takip sorusu gelince son 10 mesaj Qwen'e bağlam olarak ekleniyor. Böylece "bunu daha detaylı açıkla" gibi sorular çalışıyor.

**Semantic cache**
Exact match değil, embedding tabanlı eşleşme. "What is SVD?" ile "What is SVD?" → cache'den döner (benzerlik: ~1.0). Eşik 0.90 — çok düşük olsa yanlış cache hit riski artar, çok yüksek olsa parafrazlar yakalanamaz. Cache hit'te latency: ~150ms vs full flow: ~38 saniye.

**Exponential backoff**
Ollama hata verirse: 2sn bekle → tekrar dene → 4sn bekle → tekrar dene → hata fırlat. Geçici ağ sorunlarında sistemi çökertmez.

**Structured logging**
Her log satırı JSON — `event`, `question`, `latency_ms`, `cache_hit`, `conversation_id` alanlarıyla. Düz metin log filtrelenemiyor, JSON log sorgulanabilir.

---

## Schema Değişiklikleri

```python
# ChatRequest
conversation_id: Optional[str] = None   # eklendi

# ChatResponse
cache_hit: bool                          # eklendi
conversation_id: Optional[str] = None   # eklendi
```

---

## Karşılaşılan Sorunlar

| Sorun | Çözüm |
|---|---|
| Port 5432 zaten kullanımda | Docker dış portu 5433 yapıldı |
| SQLAlchemy commit sonrası UUID dönmüyordu | UUID manuel üretildi (`str(uuid.uuid4())`) |
| Cache hit olunca conversation_id null | Beklenen davranış — cache hit'te DB'ye gidilmiyor |
| `.claude/settings.local.json` git'e giriyordu | `.gitignore`'a `.claude/` eklendi |

---

## Servisler (Güncel)

| Servis | Nerede | Adres |
|---|---|---|
| Ollama | Host makine | localhost:11434 |
| Qdrant | Docker | localhost:6333 |
| PostgreSQL | Docker | localhost:5433 (dış) / postgres:5432 (Docker içi) |
| Redis | Docker | localhost:6379 |
| API | Docker | localhost:8000 |
