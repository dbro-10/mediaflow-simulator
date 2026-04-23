"""
content_asset.py

Defines the ContentAsset database model.
Represents a single piece of TV/video content entering the supply pipeline.
Inspired by how ITV would track a programme from production house to screen.
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class ContentAsset(Base):
    """
    A content asset is any piece of video content moving through the pipeline.
    Could be a drama episode, a news package, a sport highlight, a documentary.

    The 'current_stage' field is a quick-read snapshot of where the asset is now.
    The full history lives in the WorkflowStep table.
    """

    __tablename__ = "content_assets"

    # Primary key — SQLAlchemy auto-increments this
    id = Column(Integer, primary_key=True, index=True)

    # --- Core identity ---
    title = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)          # e.g. "Mammoth Screen", "ITV Studios"

    # --- Technical metadata ---
    duration_seconds = Column(Integer, nullable=False)  # Store as seconds, display as HH:MM:SS
    format = Column(String, nullable=False)              # e.g. "HD", "4K", "SDR", "HDR"

    # --- Editorial metadata ---
    series_title = Column(String, nullable=True)         # e.g. "Coronation Street"
    episode_number = Column(Integer, nullable=True)
    series_number = Column(Integer, nullable=True)

    # --- Rights information ---
    rights_territory = Column(String, nullable=False)    # e.g. "UK", "UK+ROI", "Global"
    rights_expiry = Column(DateTime, nullable=True)      # When rights expire

    # --- Pipeline state ---
    current_stage = Column(String, nullable=False, default="INGESTED")
    is_active = Column(Integer, default=1)               # Soft delete — 1=active, 0=deleted

    # --- Audit timestamps ---
    # server_default means the database sets this, not Python — more reliable
    ingest_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        """Readable string representation — useful for debugging and logs."""
        return (
            f"<ContentAsset id={self.id} "
            f"title='{self.title}' "
            f"stage={self.current_stage}>"
        )