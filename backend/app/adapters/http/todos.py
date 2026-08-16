from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.adapters.postgres.todo_store import fetch_todos, save_todo
from app.application.todo_use_cases import create_todo, list_todos
from app.domain.todo import InvalidTodoTitle, Todo, utc_now
from app.infrastructure.database import get_session

router = APIRouter(prefix="/todos", tags=["todos"])


class CreateTodoRequest(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2_000)


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    completed: bool
    created_at: datetime


def to_response(todo: Todo) -> TodoResponse:
    return TodoResponse.model_validate(todo)


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def post_todo(payload: CreateTodoRequest, session: Session = Depends(get_session)) -> TodoResponse:
    try:
        todo = create_todo(
            title=payload.title,
            description=payload.description,
            save_todo=lambda todo: save_todo(session, todo),
            new_id=uuid4,
            now=utc_now,
        )
    except InvalidTodoTitle as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return to_response(todo)


@router.get("", response_model=list[TodoResponse])
def get_todos(session: Session = Depends(get_session)) -> list[TodoResponse]:
    todos = list_todos(fetch_todos=lambda: fetch_todos(session))
    return [to_response(todo) for todo in todos]
