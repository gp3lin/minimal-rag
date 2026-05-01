import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API başlatılıyor...")
    yield
    logger.info("API kapatılıyor...")


app = FastAPI(title="Minimal RAG API", lifespan=lifespan)

from api.routes.chat import router
app.include_router(router)
