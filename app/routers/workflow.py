"""
routers/workflow.py

HTTP endpoints for pipeline workflow operations.
Delegates all logic to workflow_service — this layer handles HTTP only.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.workflow import (
    AdvanceStageRequest,
    FailStageRequest,
    WorkflowStepResponse,
)
from app.services.workflow_service import advance_asset_stage, fail_stage, retry_stage

router = APIRouter(prefix="/workflow", tags=["Workflow"])


@router.post("/{asset_id}/advance")
def advance_stage(
    asset_id: int,
    request: AdvanceStageRequest = AdvanceStageRequest(),
    db: Session = Depends(get_db),
):
    """
    Advance an asset to the next pipeline stage.
    QC and transcoding stages include automatic pass/fail simulation.
    """
    try:
        asset, step = advance_asset_stage(db, asset_id, notes=request.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": f"Asset advanced to {asset.current_stage}",
        "asset_id": asset.id,
        "title": asset.title,
        "new_stage": asset.current_stage,
        "step_status": step.status,
        "notes": step.notes,
        "error_message": step.error_message,
    }


@router.post("/{asset_id}/fail")
def fail_current_stage(
    asset_id: int,
    request: FailStageRequest,
    db: Session = Depends(get_db),
):
    """Manually mark the current stage as failed with a reason."""
    try:
        asset, step = fail_stage(db, asset_id, request.error_message, request.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": f"Stage {asset.current_stage} marked as failed",
        "asset_id": asset.id,
        "stage": asset.current_stage,
        "error_message": step.error_message,
    }


@router.post("/{asset_id}/retry")
def retry_current_stage(asset_id: int, db: Session = Depends(get_db)):
    """Retry the current failed stage."""
    try:
        asset, step = retry_stage(db, asset_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": f"Retrying {asset.current_stage}",
        "asset_id": asset.id,
        "stage": asset.current_stage,
        "retry_count": step.retry_count,
    }


@router.get("/{asset_id}/status")
def get_status(asset_id: int, db: Session = Depends(get_db)):
    """Quick status check for a single asset."""
    from app.models.content_asset import ContentAsset
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    return {
        "asset_id": asset.id,
        "title": asset.title,
        "current_stage": asset.current_stage,
        "last_updated": asset.updated_at,
    }