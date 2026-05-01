import hashlib
import logging
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))


def chunk_pages(pages: list[dict]) -> list[dict]:
    """Sayfa listesini chunk'lara böler, her chunk'a index ve MD5 hash ekler."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    chunks = []
    chunk_index = 0

    for page in pages:
        texts = splitter.split_text(page["text"])
        for text in texts:
            md5 = hashlib.md5(text.encode()).hexdigest()
            chunks.append({
                "text": text,
                "metadata": {
                    **page["metadata"],
                    "chunk_index": chunk_index,
                    "md5": md5,
                }
            })
            chunk_index += 1

    logger.info(f"Toplam {len(chunks)} chunk oluşturuldu")
    return chunks
