# Proje 3 — Agentic RAG

## Amaç

Sisteme "düşünme" yeteneği katmak. Her soru aynı yolu izlemek yerine
duruma göre farklı rotalar seçiyor.

---

## Eklenen Stack

| Bileşen | Teknoloji | Ne için |
|---|---|---|
| State machine | LangGraph 0.2.28 | Node'lar ve geçişler |
| Query rewriting | Qwen (prompt) | Belirsiz soruları netleştir |
| HyDE | Qwen (prompt) | Daha iyi retrieval |
| Self-RAG | Qwen (prompt) | Cevap yeterliliği kontrolü |
| Calculator | Python ast | Güvenli matematik işlemleri |

---

## Yeni Dosyalar

```
agent/
├── state.py    # AgentState TypedDict — node'lar arası veri
├── nodes.py    # planner, retriever, calculator, responder, evaluator
└── graph.py    # graf yapısı ve conditional edge'ler
```

---

## Graf Yapısı

```
START
  ↓
[Planner] — hesap mı?  → [Calculator] → [Responder] → [Evaluator]
          — bilgi mi?  → [Retriever]  → [Responder] → [Evaluator]
                                                            ↓
                                               yeterli?  → END
                                               yetersiz? → [Retriever] (max 2 tur)
```

---

## Node'lar

**Planner**
- Soruyu analiz eder: `"calculator"` veya `"retrieval"` kararı verir
- Bilgi sorusuysa sorguyu yeniden yazar (query rewriting)

**Retriever (HyDE)**
- Soruyu değil hayali cevabı embed eder
- "Bu sorunun cevabı nasıl olurdu?" → Qwen → embed → Qdrant
- Skor artışı: 0.62 → 0.74

**Calculator**
- LLM'den matematiksel ifadeyi çıkarır
- Python `ast` modülü ile güvenli eval — `eval()` kullanmıyor
- Qdrant'a hiç gitmiyor

**Responder**
- Calculator cevabı varsa pass-through
- Retrieval cevabı için chunk'ları + geçmişi prompt'a ekleyip Qwen'e gönderir

**Evaluator (Self-RAG)**
- "Bu cevap soruyu yanıtlıyor mu?" → Qwen → "yes" / "no"
- Yetersizse retriever'a geri döner (max 2 tur)

---

## Öğrenilen Kavramlar

**LangGraph state machine**
Sistem doğrusal değil artık. Her node state'i okur, günceller ve döner.
Edge'ler sabit veya conditional olabilir — conditional edge'ler node çıktısına göre karar verir.

**HyDE**
Soru kısa, chunk'lar uzun → vektörler birbirinden uzak. Hayali cevap
chunk'larla aynı "dilde" olduğu için benzerlik artar.

**Self-RAG döngüsü**
Cevap kalitesi kontrol edilmeden döndürülmüyor. Yetersiz cevap yeni
retrieval turuyla iyileştirilmeye çalışılıyor.

**Calculator güvenliği**
`eval()` yerine `ast.parse()` + operator map kullandık. Kullanıcı
kodu çalıştıramaz, sadece aritmetik ifadeler değerlendiriliyor.

---

## Karşılaşılan Sorunlar

| Sorun | Çözüm |
|---|---|
| LangGraph node boş dict döndüremez | Calculator sonrası responder `{"answer": state["answer"]}` döndürdü |
| Local langchain bağımlılık çakışması | Sadece Docker container etkilenmiyor, eval için ayrıca çözülecek |

---

## Ölçüm

| Metrik | Proje 1 | Proje 3 |
|---|---|---|
| Retrieval skoru (EN) | 0.62 | 0.74 (HyDE) |
| Cache hit latency | — | 140ms |
| Full flow latency | ~38sn | ~115sn (daha fazla LLM çağrısı) |

Full flow latency arttı çünkü artık tek LLM çağrısı yerine
planner + HyDE + responder + evaluator = 4 ayrı çağrı yapılıyor.
