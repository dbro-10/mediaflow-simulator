from __future__ import annotations
"""
services/workflow_service.py

Core business logic for the MediaFlow pipeline.
All workflow decisions live here — the API layer just calls these functions.

Keeping logic here (not in the routers) means it's testable, reusable,
and easy to reason about independently of HTTP concerns.
"""

import logging
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.content_asset import ContentAsset
from app.models.workflow_step import WorkflowStep, PIPELINE_STAGES

# Set up logging — every stage change gets logged with a timestamp
logger = logging.getLogger(__name__)


def get_next_stage(current_stage: str) -> str | None:
    """
    Returns the next stage in the pipeline, or None if already at the end.
    Having this as a function means the stage order is defined in one place only.
    """
    if current_stage not in PIPELINE_STAGES:
        return None
    current_index = PIPELINE_STAGES.index(current_stage)
    if current_index >= len(PIPELINE_STAGES) - 1:
        return None  # Already at DISTRIBUTION_READY
    return PIPELINE_STAGES[current_index + 1]


def simulate_qc_check() -> tuple[bool, str]:
    """
    Simulates a Quality Control check with a realistic pass/fail rate.
    In a real system this would call an actual QC tool like Cerify or Vidchecker.

    Returns: (passed: bool, message: str)
    """
    # 85% pass rate — realistic for a well-managed supply chain
    passed = random.random() > 0.15
    if passed:
        return True, "QC passed — all technical parameters within spec"
    else:
        # Simulate realistic QC failure reasons
        failures = [
            "Audio levels out of spec — peak at -8 LUFS, expected -23 LUFS",
            "Black frames detected at 00:23:14 — duration 3.2 seconds",
            "Incorrect aspect ratio — received 4:3, expected 16:9",
            "Timecode discontinuity at 00:45:02",
            "Missing audio on channel 2",
        ]
        return False, random.choice(failures)


def simulate_transcode() -> tuple[bool, str]:
    """
    Simulates transcoding — converting to delivery formats.
    In a real pipeline this would trigger jobs in a system like Elemental or Harmonic.
    """
    passed = random.random() > 0.05  # 95% success rate
    if passed:
        return True, "Transcoded to HLS (ITVX), MPEG-2 (linear), ProRes (archive)"
    return False, "Transcode failed — source codec unsupported"


def advance_asset_stage(
    db: Session,
    asset_id: int,
    notes: str | None = None
) -> tuple[ContentAsset, WorkflowStep]:
    """
    Moves an asset to the next pipeline stage.
    Applies automatic simulation logic for QC and transcoding stages.

    Returns the updated asset and the new workflow step created.
    Raises ValueError if the asset can't be advanced.
    """
    # Fetch the asset — raise clearly if not found
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")

    # Check the asset isn't already at the end of the pipeline
    next_stage = get_next_stage(asset.current_stage)
    if not next_stage:
        raise ValueError(
            f"Asset '{asset.title}' is already at DISTRIBUTION_READY — "
            f"cannot advance further"
        )

    # Mark the current stage's workflow step as PASSED
    current_step = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.asset_id == asset_id,
            WorkflowStep.stage_name == asset.current_stage,
            WorkflowStep.status.in_(["PENDING", "IN_PROGRESS"])
        )
        .first()
    )
    if current_step:
        current_step.status = "PASSED"
        current_step.completed_at = datetime.now(timezone.utc)
        current_step.notes = notes

    # Apply automatic simulation for specific stages
    stage_passed = True
    stage_notes = notes
    error_message = None

    if next_stage == "QC_CHECK":
        stage_passed, stage_notes = simulate_qc_check()
        if not stage_passed:
            error_message = stage_notes
            stage_notes = None

    elif next_stage == "TRANSCODING":
        stage_passed, stage_notes = simulate_transcode()
        if not stage_passed:
            error_message = stage_notes
            stage_notes = None

    # Create the new workflow step
    new_step = WorkflowStep(
        asset_id=asset_id,
        stage_name=next_stage,
        status="FAILED" if not stage_passed else "IN_PROGRESS",
        notes=stage_notes,
        error_message=error_message,
        started_at=datetime.now(timezone.utc),
    )
    db.add(new_step)

    # Update the asset's current stage
    asset.current_stage = next_stage

    # If the new stage failed immediately, don't advance further
    if not stage_passed:
        db.commit()
        db.refresh(asset)
        db.refresh(new_step)
        logger.warning(
            f"Asset {asset_id} ('{asset.title}') FAILED at {next_stage}: {error_message}"
        )
        return asset, new_step

    # If we just reached DISTRIBUTION_READY — log a notification
    if next_stage == "DISTRIBUTION_READY":
        new_step.status = "PASSED"
        new_step.completed_at = datetime.now(timezone.utc)
        logger.info(
            f"🎬 DISTRIBUTION READY: Asset {asset_id} ('{asset.title}') "
            f"is ready for Linear, ITVX, and B2B delivery"
        )

    db.commit()
    db.refresh(asset)
    db.refresh(new_step)

    logger.info(
        f"Asset {asset_id} ('{asset.title}') advanced to {next_stage}"
    )

    return asset, new_step


def fail_stage(
    db: Session,
    asset_id: int,
    error_message: str,
    notes: str | None = None
) -> tuple[ContentAsset, WorkflowStep]:
    """Manually marks the current stage of an asset as failed."""
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")

    step = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.asset_id == asset_id,
            WorkflowStep.stage_name == asset.current_stage,
        )
        .order_by(WorkflowStep.id.desc())
        .first()
    )

    if step:
        step.status = "FAILED"
        step.error_message = error_message
        step.notes = notes
        step.completed_at = datetime.now(timezone.utc)
    else:
        # Create a failed step if one doesn't exist
        step = WorkflowStep(
            asset_id=asset_id,
            stage_name=asset.current_stage,
            status="FAILED",
            error_message=error_message,
            notes=notes,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(step)

    db.commit()
    db.refresh(asset)
    db.refresh(step)

    logger.warning(f"Asset {asset_id} manually failed at {asset.current_stage}: {error_message}")
    return asset, step


def retry_stage(
    db: Session,
    asset_id: int,
) -> tuple[ContentAsset, WorkflowStep]:
    """
    Retries the current failed stage by creating a new workflow step.
    Increments the retry counter — in production you'd cap this.
    """
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id).first()
    if not asset:
        raise ValueError(f"Asset {asset_id} not found")

    # Find the most recent failed step
    failed_step = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.asset_id == asset_id,
            WorkflowStep.stage_name == asset.current_stage,
            WorkflowStep.status == "FAILED",
        )
        .order_by(WorkflowStep.id.desc())
        .first()
    )

    if not failed_step:
        raise ValueError(
            f"Asset {asset_id} has no failed step at stage {asset.current_stage}"
        )

    retry_count = failed_step.retry_count + 1

    new_step = WorkflowStep(
        asset_id=asset_id,
        stage_name=asset.current_stage,
        status="IN_PROGRESS",
        retry_count=retry_count,
        notes=f"Retry attempt {retry_count}",
        started_at=datetime.now(timezone.utc),
    )
    db.add(new_step)
    db.commit()
    db.refresh(new_step)

    logger.info(f"Asset {asset_id} retrying {asset.current_stage} (attempt {retry_count})")
    return asset, new_step