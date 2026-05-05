"""
FastAPI application entrypoint.

- Configures CORS for frontend access
- Creates database tables on startup
- Mounts the recipe API router
- Serves the frontend as static files
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import engine, Base
from .routers import recipes

# configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure tables exist before taking traffic
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
    yield
    logger.info("Application shutting down.")


# Initialize main app
app = FastAPI(
    title="Recipe Extractor & Meal Planner",
    description="Extract structured recipe data from blog URLs using LLM",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow local dev requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes.router)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.isdir(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    logger.warning("Frontend dir not found. API only mode.")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Recipe Extractor & Meal Planner is running."}
