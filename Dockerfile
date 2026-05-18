FROM python:3.11-slim

WORKDIR /app

COPY requirements.api.txt .

# CPU-only torch kur — CUDA kütüphaneleri olmadan ~200MB (tam CUDA: ~900MB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.api.txt

RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
