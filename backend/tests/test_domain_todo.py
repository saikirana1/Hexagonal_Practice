import pytest

from app.domain.todo import InvalidTodoTitle, NewTodo, normalize_new_todo


def test_normalize_new_todo_trims_values() -> None:
    assert normalize_new_todo("  Buy milk  ", "  two litres ") == NewTodo("Buy milk", "two litres")


def test_normalize_new_todo_rejects_blank_title() -> None:
    with pytest.raises(InvalidTodoTitle, match="must not be blank"):
        normalize_new_todo("   ", None)
