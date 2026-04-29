"""
schemas/workflow.py

Schemas for workflow operations — advancing stages, failing them, retrying.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class WorkflowStepResponse(BaseModel):
    """Returned whenever a workflow step is created or updated."""
    id: int
    asset_id: int
    stage_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    notes: Optional[str]
    error_message: Optional[str]
    retry_count: int

    model_config = {"from_attributes": True}


class AdvanceStageRequest(BaseModel):
    """Optional body when advancing to the next stage."""
    notes: Optional[str] = Field(None, description="Any notes about this stage")


class FailStageRequest(BaseModel):
    """Required body when failing a stage — must include a reason."""
    error_message: str = Field(
        ...,
        min_length=1,
        description="What went wrong — required for audit trail"
    )
    notes: Optional[str] = None


class PipelineSummary(BaseModel):
    """High level counts across the whole pipeline — for the dashboard."""
    total_assets: int
    by_stage: dict
    failed_count: int
    distribution_ready_count: int