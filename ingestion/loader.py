import logging
import pdfplumber

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_pdf(filepath: str) -> list[dict]:
    """PDF dosyasını sayfa sayfa okur, boş sayfaları atlar."""
    pages = []
    filename = filepath.split("/")[-1].split("\\")[-1]

    with pdfplumber.open(filepath) as pdf:
        logger.info(f"PDF yüklendi: {filename} ({len(pdf.pages)} sayfa)")

        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text or not text.strip():
                logger.debug(f"Sayfa {i} boş, atlanıyor")
                continue
            pages.append({
                "text": text.strip(),
                "metadata": {
                    "filename": filename,
                    "page": i,
                }
            })

    logger.info(f"Toplam {len(pages)} sayfa yüklendi (boş sayfalar hariç)")
    return pages
