"""
routers/pipeline.py

High-level pipeline visibility endpoints.
Used by the dashboard and for operational monitoring.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.content_asset import ContentAsset
from app.models.workflow_step import PIPELINE_STAGES

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.get("/summary")
def pipeline_summary(db: Session = Depends(get_db)):
    """
    Returns a count of assets at each pipeline stage.
    This is the top-level view an operations team would monitor.
    """
    assets = db.query(ContentAsset).filter(ContentAsset.is_active == 1).all()

    by_stage = {stage: 0 for stage in PIPELINE_STAGES}
    failed_count = 0

    for asset in assets:
        if asset.current_stage in by_stage:
            by_stage[asset.current_stage] += 1

    # Count assets with a current failed step
    from app.models.workflow_step import WorkflowStep
    failed_count = (
        db.query(WorkflowStep)
        .join(ContentAsset, WorkflowStep.asset_id == ContentAsset.id)
        .filter(
            WorkflowStep.status == "FAILED",
            ContentAsset.is_active == 1,
        )
        .distinct(WorkflowStep.asset_id)
        .count()
    )

    return {
        "total_assets": len(assets),
        "by_stage": by_stage,
        "failed_count": failed_count,
        "distribution_ready_count": by_stage.get("DISTRIBUTION_READY", 0),
    }


@router.get("/search")
def search_assets(
    title: Optional[str] = Query(None, description="Search by title (partial match)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    db: Session = Depends(get_db),
):
    """
    Search and filter assets across the pipeline.
    Supports partial title matching and filtering by source or stage.
    """
    query = db.query(ContentAsset).filter(ContentAsset.is_active == 1)

    if title:
        query = query.filter(ContentAsset.title.ilike(f"%{title}%"))
    if source:
        query = query.filter(ContentAsset.source.ilike(f"%{source}%"))
    if stage:
        query = query.filter(ContentAsset.current_stage == stage.upper())

    results = query.order_by(ContentAsset.ingest_timestamp.desc()).all()

    return {
        "count": len(results),
        "results": [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "current_stage": a.current_stage,
                "ingest_timestamp": a.ingest_timestamp,
            }
            for a in results
        ],
    }


@router.get("/distribution-ready")
def distribution_ready(db: Session = Depends(get_db)):
    """
    Returns all assets ready for distribution.
    In a real system this would trigger delivery to Linear, ITVX, and B2B partners.
    """
    assets = db.query(ContentAsset).filter(
        ContentAsset.current_stage == "DISTRIBUTION_READY",
        ContentAsset.is_active == 1,
    ).all()

    return {
        "count": len(assets),
        "assets": [
            {
                "id": a.id,
                "title": a.title,
                "source": a.source,
                "format": a.format,
                "rights_territory": a.rights_territory,
                "rights_expiry": a.rights_expiry,
            }
            for a in assets
        ],
    }