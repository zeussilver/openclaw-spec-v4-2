"""Queue data models for Day Logger."""

from datetime import datetime

from pydantic import BaseModel, Field


class QueueItem(BaseModel):
    """A single item in the nightly queue."""

    id: str
    capability: str
    first_seen: datetime
    occurrences: int = 1
    context: str = ""
    status: str = Field(default="pending")  # pending | processing | completed | failed


class NightlyQueue(BaseModel):
    """The nightly queue containing items to be processed."""

    items: list[QueueItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)
