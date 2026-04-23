"""
workflow_step.py

Defines the WorkflowStep model — an immutable log of every stage
a content asset passes through in the supply pipeline.

Every time an asset moves to a new stage, a new row is written here.
Rows are never updated or deleted — this gives us a complete audit trail.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


# These are all the valid stages in the pipeline — in order.
# Storing them here means we can validate against this list anywhere in the app.
PIPELINE_STAGES = [
    "INGESTED",
    "METADATA_VALIDATION",
    "QC_CHECK",
    "TRANSCODING",
    "RIGHTS_COMPLIANCE",
    "ARCHIVING",
    "DISTRIBUTION_READY",
]

# These are the valid statuses a stage can have
STAGE_STATUSES = [
    "PENDING",      # Stage has been created but not started
    "IN_PROGRESS",  # Stage is currently running
    "PASSED",       # Stage completed successfully
    "FAILED",       # Stage failed — see error_message for reason
    "RETRYING",     # Stage failed and is being retried
]


class WorkflowStep(Base):
    """
    A single step in an asset's journey through the pipeline.

    One ContentAsset will have many WorkflowSteps over its lifetime.
    This table is append-only — we only ever INSERT, never UPDATE or DELETE.
    This gives us a complete, trustworthy audit trail.
    """

    __tablename__ = "workflow_steps"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking back to the content asset
    # ondelete="CASCADE" means if the asset is deleted, its steps are too
    asset_id = Column(
        Integer,
        ForeignKey("content_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # --- Stage information ---
    stage_name = Column(String, nullable=False)    # Must be one of PIPELINE_STAGES
    status = Column(String, nullable=False, default="PENDING")

    # --- Timing ---
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)  # Null until the stage finishes

    # --- Outcome details ---
    notes = Column(String, nullable=True)           # Any useful context
    error_message = Column(String, nullable=True)   # Populated if status is FAILED
    retry_count = Column(Integer, default=0)        # How many times this stage was retried

    # --- Relationship back to the asset ---
    # This lets us write: step.asset to get the parent ContentAsset object
    asset = relationship("ContentAsset", backref="workflow_steps")

    def __repr__(self):
        return (
            f"<WorkflowStep id={self.id} "
            f"asset_id={self.asset_id} "
            f"stage={self.stage_name} "
            f"status={self.status}>"
        )