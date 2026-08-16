from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.domain.todo import Todo, normalize_new_todo
from app.ports.todo_store import ListTodos, SaveTodo


def create_todo(
    *,
    title: str,
    description: str | None,
    save_todo: SaveTodo,
    new_id: Callable[[], UUID],
    now: Callable[[], datetime],
) -> Todo:
    """Create a Todo by composing pure validation with injected effects."""
    draft = normalize_new_todo(title, description)
    todo = Todo(
        id=new_id(),
        title=draft.title,
        description=draft.description,
        completed=False,
        created_at=now(),
    )
    return save_todo(todo)


def list_todos(*, fetch_todos: ListTodos) -> list[Todo]:
    return fetch_todos()
