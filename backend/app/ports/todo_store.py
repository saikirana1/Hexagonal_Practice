from collections.abc import Callable

from app.domain.todo import Todo

SaveTodo = Callable[[Todo], Todo]
ListTodos = Callable[[], list[Todo]]
