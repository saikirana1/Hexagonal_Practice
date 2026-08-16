from fastapi import FastAPI

from app.adapters.http.todos import router as todos_router

app = FastAPI(title="Todo API", version="0.1.0")
app.include_router(todos_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
