import json
import logging
import os
from pathlib import Path

import httpx
from datasets import Dataset
from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, faithfulness

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

ragas_llm = LangchainLLMWrapper(ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL))
ragas_embeddings = LangchainEmbeddingsWrapper(OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL))
DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def query_api(question: str) -> dict:
    response = httpx.post(
        f"{API_BASE_URL}/chat",
        json={"message": question},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def build_ragas_dataset(golden: list[dict]) -> tuple[Dataset, list[dict]]:
    rows = []
    raw_results = []

    for item in golden:
        logger.info(f"[{item['lang'].upper()}] Sorgu: {item['question']}")
        result = query_api(item["question"])

        rows.append({
            "question": item["question"],
            "answer": result["answer"],
            "contexts": [c["text"] for c in result["citations"]],
            "ground_truth": item["ground_truth"],
        })
        raw_results.append({
            "id": item["id"],
            "lang": item["lang"],
            "question": item["question"],
            "answer": result["answer"],
            "citations": result["citations"],
            "latency_ms": result["latency_ms"],
        })

    return Dataset.from_list(rows), raw_results


def compare_languages(scores: list[dict]) -> dict:
    tr = [s for s in scores if s["lang"] == "tr"]
    en = [s for s in scores if s["lang"] == "en"]

    def avg(items, key):
        values = [i[key] for i in items if i.get(key) is not None]
        return round(sum(values) / len(values), 4) if values else None

    return {
        "tr": {
            "faithfulness": avg(tr, "faithfulness"),
            "answer_relevancy": avg(tr, "answer_relevancy"),
        },
        "en": {
            "faithfulness": avg(en, "faithfulness"),
            "answer_relevancy": avg(en, "answer_relevancy"),
        },
    }


def main():
    with open(DATASET_PATH, encoding="utf-8") as f:
        golden = json.load(f)

    logger.info(f"{len(golden)} soru yüklendi")
    dataset, raw_results = build_ragas_dataset(golden)

    logger.info("RAGAS metrikleri hesaplanıyor...")
    ragas_result = evaluate(dataset, metrics=[faithfulness, answer_relevancy], llm=ragas_llm, embeddings=ragas_embeddings)
    ragas_df = ragas_result.to_pandas()

    scores = []
    for i, item in enumerate(raw_results):
        scores.append({
            **item,
            "faithfulness": ragas_df.iloc[i]["faithfulness"],
            "answer_relevancy": ragas_df.iloc[i]["answer_relevancy"],
        })

    comparison = compare_languages(scores)
    report = {"scores": scores, "language_comparison": comparison}

    REPORTS_DIR.mkdir(exist_ok=True)
    output_path = REPORTS_DIR / "results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"Sonuçlar kaydedildi: {output_path}")
    logger.info(f"TR — faithfulness: {comparison['tr']['faithfulness']}, relevancy: {comparison['tr']['answer_relevancy']}")
    logger.info(f"EN — faithfulness: {comparison['en']['faithfulness']}, relevancy: {comparison['en']['answer_relevancy']}")


if __name__ == "__main__":
    main()
