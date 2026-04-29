"""
main.py

Application entry point. Creates database tables and registers all routers.
"""

import logging
from fastapi import FastAPI
from app.database import engine, Base
from app.models import ContentAsset, WorkflowStep
from app.routers import assets, workflow, pipeline

# Configure logging — every module's logger writes here
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MediaFlow Simulator",
    description=(
        "A simulation of ITV's content supply pipeline — "
        "tracking TV assets from ingest through to distribution on "
        "Linear TV, ITVX (VoD), and B2B partners."
    ),
    version="0.1.0",
)

# Register all routers
app.include_router(assets.router)
app.include_router(workflow.router)
app.include_router(pipeline.router)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "running",
        "project": "MediaFlow Simulator",
        "version": "0.1.0",
    }