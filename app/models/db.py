import uuid
from datetime import datetime
import datetime as dt

from sqlmodel import SQLModel, Field as F


def _utcnow():
    return datetime.now(dt.UTC)


class DragBase(SQLModel):
    created_at: datetime = F(default_factory=_utcnow)
    updated_at: datetime = F(default_factory=_utcnow)


class DocumentationSet(DragBase, table=True):
    __tablename__ = "documentation_sets"  # type: ignore

    id: uuid.UUID = F(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    name: str = F(index=True, unique=True)
    root_url: str
    total_chunks: int = F(default=0)


class IngestionTask(DragBase, table=True):
    __tablename__ = "ingestion_tasks"  # type: ignore

    id: uuid.UUID = F(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    documentation_set_id: uuid.UUID | None = F(foreign_key="documentation_sets.id")
    status: str
    error_message: str | None = None
    url: str
