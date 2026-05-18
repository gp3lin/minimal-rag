"""
Chunk'lardan entity ve ilişki çıkarır, Neo4j'e yazar.
LLM yerine spaCy kullanır — noun chunk'ları entity, aynı chunk'ta
geçen çiftler RELATED_TO ilişkisi olarak modellenir.

Graph şeması:
  (:Entity {name}) -[:RELATED_TO {relation, chunk_text, chunk_id}]-> (:Entity)
"""
import itertools
import logging
import os
import uuid

import spacy
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "ragpassword")

MIN_ENTITY_LENGTH = 3    # çok kısa token'ları atla ("a", "an", "the" vs.)
MAX_PAIRS_PER_CHUNK = 10  # chunk başına max ilişki sayısı


def _load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        raise RuntimeError(
            "spaCy modeli bulunamadı. Çalıştır: python -m spacy download en_core_web_sm"
        )


def _extract_triples(nlp, chunk_text: str, chunk_id: str) -> list[dict]:
    """Chunk'tan noun chunk çiftlerini entity+ilişki olarak çıkarır."""
    doc = nlp(chunk_text)

    # Noun chunk'ları temizle ve filtrele
    entities = []
    for chunk in doc.noun_chunks:
        name = chunk.root.text.lower().strip()
        if len(name) >= MIN_ENTITY_LENGTH and not chunk.root.is_stop:
            entities.append(name)

    # Tekrarları kaldır, sırayı koru
    seen = set()
    unique_entities = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            unique_entities.append(e)

    # Her entity çiftini ilişki olarak üret (max MAX_PAIRS_PER_CHUNK)
    pairs = list(itertools.combinations(unique_entities, 2))[:MAX_PAIRS_PER_CHUNK]

    return [
        {"subject": s, "relation": "co-occurs", "object": o, "chunk_text": chunk_text, "chunk_id": chunk_id}
        for s, o in pairs
    ]


def _write_triples(driver, triples: list[dict]) -> None:
    if not triples:
        return
    with driver.session() as session:
        for t in triples:
            session.run(
                """
                MERGE (s:Entity {name: $subject})
                MERGE (o:Entity {name: $object})
                CREATE (s)-[:RELATED_TO {relation: $relation, chunk_text: $chunk_text, chunk_id: $chunk_id}]->(o)
                """,
                subject=t["subject"],
                object=t["object"],
                relation=t["relation"],
                chunk_text=t["chunk_text"],
                chunk_id=t["chunk_id"],
            )


def build_knowledge_graph(chunks: list[dict]) -> None:
    """Tüm chunk'ları işler, Neo4j'e graph yazar."""
    nlp = _load_nlp()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("Neo4j temizlendi")

    total_triples = 0
    for i, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        triples = _extract_triples(nlp, chunk["text"], chunk_id)
        _write_triples(driver, triples)
        total_triples += len(triples)

        if (i + 1) % 50 == 0:
            logger.info(f"Graph extraction: {i + 1}/{len(chunks)} chunk işlendi")

    driver.close()
    logger.info(f"Knowledge graph tamamlandı: {len(chunks)} chunk, {total_triples} triple")
