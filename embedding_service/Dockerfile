FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# CPU-only torch: GPU sürümüne göre ~1.5GB daha küçük
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Model image içine gömülür, her container başlatmada indirilmez
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY serve_app.py .

EXPOSE 8001

CMD ["uvicorn", "serve_app:app", "--host", "0.0.0.0", "--port", "8001"]
