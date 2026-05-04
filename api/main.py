import structlog
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI

from db.database import engine
from db.models import Base

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api_starting")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("db_tables_ready")
    yield
    logger.info("api_stopping")


app = FastAPI(title="Minimal RAG API", lifespan=lifespan)

from api.routes.chat import router
app.include_router(router)
