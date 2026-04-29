"""
routers/assets.py

HTTP endpoints for content asset CRUD operations.
Routers handle HTTP concerns only — business logic lives in services.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.content_asset import ContentAsset
from app.models.workflow_step import WorkflowStep, PIPELINE_STAGES
from app.schemas.asset import AssetCreate, AssetResponse, AssetSummary

logger = logging.getLogger(__name__)

# APIRouter groups related endpoints — main.py mounts this with a prefix
router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post("/", response_model=AssetResponse, status_code=201)
def create_asset(asset_data: AssetCreate, db: Session = Depends(get_db)):
    """
    Ingest a new content asset into the pipeline.
    Automatically creates the first workflow step (INGESTED).
    """
    # Create the asset record
    new_asset = ContentAsset(**asset_data.model_dump())
    db.add(new_asset)
    db.flush()  # Gets us the auto-generated ID without a full commit

    # Create the initial workflow step — every asset starts at INGESTED
    initial_step = WorkflowStep(
        asset_id=new_asset.id,
        stage_name="INGESTED",
        status="PASSED",  # Being ingested IS the first stage passing
    )
    db.add(initial_step)
    db.commit()
    db.refresh(new_asset)

    logger.info(f"New asset ingested: '{new_asset.title}' (id={new_asset.id})")
    return new_asset


@router.get("/", response_model=List[AssetSummary])
def list_assets(
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    db: Session = Depends(get_db)
):
    """
    List all active assets. Optionally filter by current pipeline stage.
    """
    query = db.query(ContentAsset).filter(ContentAsset.is_active == 1)

    if stage:
        stage_upper = stage.upper()
        if stage_upper not in PIPELINE_STAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage. Must be one of: {', '.join(PIPELINE_STAGES)}"
            )
        query = query.filter(ContentAsset.current_stage == stage_upper)

    return query.order_by(ContentAsset.ingest_timestamp.desc()).all()


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """Get full details of a single asset."""
    asset = db.query(ContentAsset).filter(
        ContentAsset.id == asset_id,
        ContentAsset.is_active == 1
    ).first()

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    return asset


@router.get("/{asset_id}/history")
def get_asset_history(asset_id: int, db: Session = Depends(get_db)):
    """
    Returns the full workflow history for an asset.
    This is the complete audit trail — every stage, pass, fail, and retry.
    """
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    steps = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.asset_id == asset_id)
        .order_by(WorkflowStep.started_at.asc())
        .all()
    )

    return {
        "asset_id": asset_id,
        "title": asset.title,
        "current_stage": asset.current_stage,
        "history": [
            {
                "id": s.id,
                "stage_name": s.stage_name,
                "status": s.status,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "notes": s.notes,
                "error_message": s.error_message,
                "retry_count": s.retry_count,
            }
            for s in steps
        ],
    }


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """
    Soft-delete an asset — marks it inactive rather than removing it.
    Data is never truly deleted; this preserves the audit trail.
    """
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    asset.is_active = 0
    db.commit()
    logger.info(f"Asset {asset_id} ('{asset.title}') soft-deleted")