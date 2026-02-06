from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.db.models import Task
from app.db.session import get_session

router = APIRouter()


@router.post("/", response_model=Task)
def create_task(task: Task) -> Task:
    with get_session() as session:
        session.add(task)
        session.commit()
        session.refresh(task)
        return task


@router.get("/", response_model=List[Task])
def list_tasks() -> List[Task]:
    with get_session() as session:
        return list(session.exec(select(Task)))


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
