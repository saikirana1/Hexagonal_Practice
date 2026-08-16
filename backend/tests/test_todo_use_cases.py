from datetime import UTC, datetime
from uuid import UUID

from app.application.todo_use_cases import create_todo, list_todos
from app.domain.todo import Todo


def test_create_todo_composes_injected_dependencies() -> None:
    expected_id = UUID("12345678-1234-5678-1234-567812345678")
    expected_time = datetime(2026, 8, 16, tzinfo=UTC)
    saved: list[Todo] = []

    todo = create_todo(
        title="  Write tests ",
        description=None,
        save_todo=lambda value: saved.append(value) or value,
        new_id=lambda: expected_id,
        now=lambda: expected_time,
    )

    assert todo == Todo(expected_id, "Write tests", None, False, expected_time)
    assert saved == [todo]


def test_list_todos_delegates_to_read_port() -> None:
    todo = Todo(UUID(int=1), "Read", None, False, datetime(2026, 8, 16, tzinfo=UTC))
    assert list_todos(fetch_todos=lambda: [todo]) == [todo]
