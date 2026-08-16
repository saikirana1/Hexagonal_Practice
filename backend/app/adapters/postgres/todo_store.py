from sqlmodel import Session, select

from app.adapters.postgres.models import TodoRow
from app.domain.todo import Todo


def to_row(todo: Todo) -> TodoRow:
    return TodoRow(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        created_at=todo.created_at,
    )


def to_domain(row: TodoRow) -> Todo:
    return Todo(
        id=row.id,
        title=row.title,
        description=row.description,
        completed=row.completed,
        created_at=row.created_at,
    )


def save_todo(session: Session, todo: Todo) -> Todo:
    row = to_row(todo)
    session.add(row)
    session.commit()
    session.refresh(row)
    return to_domain(row)


def fetch_todos(session: Session) -> list[Todo]:
    statement = select(TodoRow).order_by(TodoRow.created_at.desc())
    return [to_domain(row) for row in session.exec(statement).all()]
