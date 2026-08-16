from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


class InvalidTodoTitle(ValueError):
    """Raised when a Todo title violates domain rules."""


@dataclass(frozen=True, slots=True)
class NewTodo:
    title: str
    description: str | None


@dataclass(frozen=True, slots=True)
class Todo:
    id: UUID
    title: str
    description: str | None
    completed: bool
    created_at: datetime


def normalize_new_todo(title: str, description: str | None) -> NewTodo:
    """Validate and normalize user input without side effects."""
    normalized_title = title.strip()
    normalized_description = description.strip() if description else None

    if not normalized_title:
        raise InvalidTodoTitle("title must not be blank")
    if len(normalized_title) > 200:
        raise InvalidTodoTitle("title must be 200 characters or fewer")
    if normalized_description and len(normalized_description) > 2_000:
        raise InvalidTodoTitle("description must be 2000 characters or fewer")

    return NewTodo(title=normalized_title, description=normalized_description)


def utc_now() -> datetime:
    return datetime.now(UTC)
