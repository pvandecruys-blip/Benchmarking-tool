"""
SourceLens — FastAPI Main Application
Entry point for the backend server.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes import projects, files, analysis, outputs, config_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sourcelens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    settings = get_settings()
    from app.services.llm_client import has_api_key
    logger.info("=" * 60)
    logger.info("  SourceLens — AI-Powered Benchmarking Audit Tool")
    logger.info("=" * 60)
    logger.info(f"  Data directory: {settings.data_dir}")
    logger.info(f"  LLM model: {settings.llm_model}")
    logger.info(f"  Google API key: {'Yes' if settings.google_api_key else 'No'}")
    logger.info(f"  OpenAI API key: {'Yes' if settings.openai_api_key else 'No'}")
    logger.info(f"  Demo mode: {'ON' if settings.demo_mode or not has_api_key() else 'OFF'}")
    logger.info("=" * 60)
    yield
    logger.info("SourceLens shutting down")


app = FastAPI(
    title="SourceLens API",
    description="AI-powered benchmarking audit & source verification tool",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (allow frontend dev server)
settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(analysis.router)
app.include_router(outputs.router)
app.include_router(config_routes.router)


@app.get("/")
async def root():
    return {
        "name": "SourceLens API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    settings = get_settings()
    from app.services.llm_client import has_api_key
    return {
        "status": "healthy",
        "has_api_key": has_api_key(),
        "has_google_key": bool(settings.google_api_key),
        "has_openai_key": bool(settings.openai_api_key),
        "llm_model": settings.llm_model,
        "demo_mode": settings.demo_mode,
    }
