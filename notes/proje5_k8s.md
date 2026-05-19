# Proje 5 — Scalable Infrastructure

## Hedef
Sistemi Kubernetes'e taşımak, embedding servisini bağımsız ölçeklendirmek,
HPA ile otomatik pod yönetimini gözlemlemek.

## Mimari Değişikliği

```
Proje 4:  API → Ollama (embed + LLM)  +  Neo4j
Proje 5:  API → Ray Serve (embed)
               → Ollama (LLM only)
               → Neo4j (K8s veya Docker)
```

### Neden Ollama'dan ayrıldık?
- Ollama embedding için çok ağır: host'ta çalışıyor, K8s içinden erişim kırgın
- sentence-transformers modeli (~80MB) pod içinde yüklü → gerçek bağımsızlık
- HPA embedding pod'unu scale edebilir, Ollama darboğaz olmaz

## Yeni Bileşenler

### Ray Serve Embedding Servisi (`embedding_service/`)
- Model: `all-MiniLM-L6-v2` (384-dim, normalize_embeddings=True)
- Endpoint: `POST /embed` → `{"embedding": [...], "dim": 384}`
- `GET /health` → readiness probe olarak kullanılır
- `lru_cache` ile model singleton (her replica bir kez yükler)

### K8s Manifestleri (`k8s/`)
| Dosya | İçerik |
|---|---|
| `embedding-deployment.yaml` | Deployment + ClusterIP Service |
| `api-deployment.yaml` | Deployment + LoadBalancer Service |
| `hpa.yaml` | HPA: %50 CPU → 1–4 replica |

### Load Test (`load_test/locustfile.py`)
- 5 farklı soru pool'u, random seçim
- `wait_time = between(1, 3)` saniye
- `/health` de test edilir (oran: 3x)

## Çalıştırma Sırası

### 1. Embedding servisini lokalde test et
```bash
pip install ray[serve] sentence-transformers fastapi
cd embedding_service
serve run serve_app:embedding_app --host 0.0.0.0 --port 8001
```

### 2. Yeni embedding ile ingestion (Qdrant koleksiyonu silinip yeniden oluşturulur)
```bash
# .env içinde EMBED_SERVICE_URL=http://localhost:8001 olduğundan emin ol
cd ingestion
python indexer.py ../data/papers/matrix_methods.pdf
```

### 3. API'yi yeniden build et (searcher.py değişti)
```bash
docker compose up -d --build api
```

### 4. minikube kurulumu
```bash
minikube start --cpus 4 --memory 6144
minikube addons enable metrics-server   # HPA için şart
```

### 5. Embedding image'ını minikube'a yükle
```bash
cd embedding_service
docker build -t scalableragsystem-embedding:latest .
minikube image load scalableragsystem-embedding:latest
```

### 6. K8s'e deploy et
```bash
# Qdrant ve Neo4j Helm ile
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm install qdrant qdrant/qdrant

helm repo add neo4j https://helm.neo4j.com/neo4j
helm install neo4j neo4j/neo4j --set neo4j.password=ragpassword

# Embedding servisi ve API
kubectl apply -f k8s/embedding-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/hpa.yaml
```

### 7. Load test
```bash
pip install locust
locust -f load_test/locustfile.py --host http://$(minikube service rag-api --url)
# Web UI: http://localhost:8089
```

### 8. HPA gözlemi
```bash
# Ayrı terminalde izle:
kubectl get hpa embedding-service-hpa --watch
kubectl get pods --watch
```

## Beklenen Gözlem
- Locust kullanıcı sayısı artınca embedding pod CPU yükselir
- HPA %50 eşiği geçince yeni pod açar (1 → 2 → 4)
- Locust durduğunda pod sayısı tekrar 1'e düşer

## Notlar
- `imagePullPolicy: Never` → minikube local image kullanır, registry gerekmez
- `host.minikube.internal` → minikube pod'larından host makineye erişim (Ollama için)
- VECTOR_SIZE 768'den 384'e değişti → eski Qdrant koleksiyonu silinmeli
