"""
schemas/asset.py

Pydantic schemas define the shape of data entering and leaving the API.
Separate from database models — what we store vs what we expose are different concerns.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class AssetCreate(BaseModel):
    """
    Schema for creating a new content asset.
    This is what the client sends in the POST /assets request body.
    """
    title: str = Field(..., min_length=1, max_length=255, description="Programme title")
    source: str = Field(..., min_length=1, description="Production house or source")
    duration_seconds: int = Field(..., gt=0, description="Duration in seconds")
    format: str = Field(..., description="e.g. HD, 4K, SDR, HDR")
    series_title: Optional[str] = Field(None, description="Series name if applicable")
    episode_number: Optional[int] = Field(None, gt=0)
    series_number: Optional[int] = Field(None, gt=0)
    rights_territory: str = Field(..., description="e.g. UK, UK+ROI, Global")
    rights_expiry: Optional[datetime] = None

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        """Only accept known formats — prevents garbage data entering the system."""
        allowed = {"HD", "4K", "SDR", "HDR", "SD"}
        if v.upper() not in allowed:
            raise ValueError(f"Format must be one of: {', '.join(allowed)}")
        return v.upper()


class AssetResponse(BaseModel):
    """
    Schema for returning asset data to the client.
    Includes database-generated fields like id and timestamps.
    """
    id: int
    title: str
    source: str
    duration_seconds: int
    format: str
    series_title: Optional[str]
    episode_number: Optional[int]
    series_number: Optional[int]
    rights_territory: str
    rights_expiry: Optional[datetime]
    current_stage: str
    ingest_timestamp: datetime
    updated_at: Optional[datetime]

    # This tells Pydantic to read from SQLAlchemy model attributes
    model_config = {"from_attributes": True}


class AssetSummary(BaseModel):
    """
    Lightweight schema for list views — only what's needed at a glance.
    Returning full objects in list endpoints wastes bandwidth.
    """
    id: int
    title: str
    source: str
    current_stage: str
    ingest_timestamp: datetime

    model_config = {"from_attributes": True}