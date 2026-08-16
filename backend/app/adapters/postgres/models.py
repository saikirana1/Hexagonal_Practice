from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


class TodoRow(SQLModel, table=True):
    __tablename__ = "todos"

    id: UUID = Field(primary_key=True)
    title: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    completed: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
