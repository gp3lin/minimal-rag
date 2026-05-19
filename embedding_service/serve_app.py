"""
Embedding mikroservisi — FastAPI + sentence-transformers
Model: all-MiniLM-L6-v2 (384-dim)
Endpoint: POST /embed  {"text": "..."}  →  {"embedding": [...], "dim": 384}

Lokal geliştirme: python serve_app.py  (Ray Serve ile)
K8s / Docker:     uvicorn serve_app:app --host 0.0.0.0 --port 8001
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

app = FastAPI()
model = SentenceTransformer(MODEL_NAME)


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim: int


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vector = model.encode(req.text, normalize_embeddings=True).tolist()
    return EmbedResponse(embedding=vector, dim=len(vector))


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
