"""
CodeTrace AI — FastAPI Application

Entry point for the backend server.

Start with:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.execute import router as execute_router
from .api.lint import router as lint_router
from .api.fix import router as fix_router
from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"CodeTrace AI starting on {settings.HOST}:{settings.PORT}")
    logger.info(f"Execution mode: {settings.EXECUTION_MODE}")
    logger.info(f"CORS origins: {settings.cors_origins}")
    logger.info(f"AI configured: {settings.ai_configured}")
    yield
    logger.info("CodeTrace AI shutting down")


app = FastAPI(
    title="CodeTrace AI",
    description="Intelligent Python debugging and execution visualization platform.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — allow configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(execute_router, prefix="/api")
app.include_router(lint_router, prefix="/api")
app.include_router(fix_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "CodeTrace AI",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }
