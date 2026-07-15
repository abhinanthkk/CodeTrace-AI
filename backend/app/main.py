"""
CodeTrace AI — FastAPI Application

Entry point for the backend server.

Start with:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.execute import router as execute_router
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"CodeTrace AI starting on {settings.HOST}:{settings.PORT}")
    logger.info(f"CORS origin: {settings.CORS_ORIGIN}")
    logger.info(f"Sandbox image: {settings.SANDBOX_IMAGE}")
    logger.info(f"AI configured: {settings.ai_configured}")
    yield
    logger.info("CodeTrace AI shutting down")


# Create FastAPI app
app = FastAPI(
    title="CodeTrace AI",
    description="Intelligent Python debugging and execution visualization platform.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(execute_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "CodeTrace AI",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }
