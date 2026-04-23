"""
main.py

Entry point for the MediaFlow FastAPI application.
Creates database tables on startup and mounts all routers.
"""

from fastapi import FastAPI
from app.database import engine
from app.models import ContentAsset, WorkflowStep

# Create all database tables if they don't already exist.
# In production this would be handled by a migration tool like Alembic.
from app.database import Base
Base.metadata.create_all(bind=engine)

# Initialise the FastAPI app
app = FastAPI(
    title="MediaFlow Simulator",
    description="A simulation of ITV's content supply pipeline — from ingest to distribution.",
    version="0.1.0",
)


@app.get("/")
def health_check():
    """Simple health check — confirms the API is running."""
    return {
        "status": "running",
        "project": "MediaFlow Simulator",
        "version": "0.1.0",
    }