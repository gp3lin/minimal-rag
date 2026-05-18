"""
Neo4j graph search: sorgudan spaCy ile entity çıkar, bağlı chunk'ları döner.
"""
import logging
import os
from functools import lru_cache

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "ragpassword")
GRAPH_TOP_K = int(os.getenv("GRAPH_TOP_K", 5))


@lru_cache(maxsize=1)
def _load_nlp():
    import spacy
    return spacy.load("en_core_web_sm")


def _extract_query_entities(question: str) -> list[str]:
    """spaCy ile sorgudan noun chunk'ları çıkarır."""
    nlp = _load_nlp()
    doc = nlp(question)
    entities = []
    for chunk in doc.noun_chunks:
        name = chunk.root.text.lower().strip()
        if len(name) >= 3 and not chunk.root.is_stop:
            entities.append(name)
    return list(dict.fromkeys(entities))[:5]


def graph_search(question: str) -> list[dict]:
    """Entity'lere bağlı chunk'ları Neo4j'den getirir."""
    entities = _extract_query_entities(question)
    if not entities:
        return []

    logger.info(f"Graph search entities: {entities}")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    chunks = []
    seen_ids = set()

    with driver.session() as session:
        for entity in entities:
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS toLower($name)
                MATCH (e)-[r:RELATED_TO]-(other:Entity)
                RETURN r.chunk_text AS text, r.chunk_id AS chunk_id, r.relation AS relation,
                       e.name AS entity, other.name AS other_entity
                LIMIT $limit
                """,
                name=entity,
                limit=GRAPH_TOP_K,
            )
            for record in result:
                cid = record["chunk_id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    chunks.append({
                        "text": record["text"],
                        "source": "graph",
                        "page": 0,
                        "score": 0.7,
                        "graph_context": f"{record['entity']} → {record['relation']} → {record['other_entity']}",
                    })

    driver.close()
    logger.info(f"Graph search: {len(chunks)} chunk bulundu")
    return chunks
