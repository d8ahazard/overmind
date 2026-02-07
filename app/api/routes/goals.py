from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.db.models import ProjectGoal
from app.db.session import get_session

router = APIRouter()


@router.get("/", response_model=List[ProjectGoal])
def list_goals(request: Request, status: Optional[str] = None) -> List[ProjectGoal]:
    project_id = request.app.state.active_project_id
    if project_id is None:
        raise HTTPException(status_code=404, detail="No active project")
    with get_session() as session:
        query = select(ProjectGoal).where(ProjectGoal.project_id == project_id)
        if status:
            query = query.where(ProjectGoal.status == status)
        return list(session.exec(query))


@router.post("/", response_model=ProjectGoal)
def create_goal(payload: dict, request: Request) -> ProjectGoal:
    project_id = request.app.state.active_project_id
    if project_id is None:
        raise HTTPException(status_code=404, detail="No active project")
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    goal = ProjectGoal(
        project_id=project_id,
        run_id=payload.get("run_id"),
        task_id=payload.get("task_id"),
        title=title,
        description=payload.get("description"),
        status=payload.get("status") or "open",
    )
    with get_session() as session:
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal


@router.put("/{goal_id}", response_model=ProjectGoal)
def update_goal(goal_id: int, payload: dict, request: Request) -> ProjectGoal:
    with get_session() as session:
        goal = session.get(ProjectGoal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        if payload.get("title") is not None:
            goal.title = str(payload.get("title") or "").strip() or goal.title
        if "description" in payload:
            goal.description = payload.get("description")
        if payload.get("status") is not None:
            goal.status = str(payload.get("status") or goal.status)
        if payload.get("run_id") is not None:
            goal.run_id = payload.get("run_id")
        if payload.get("task_id") is not None:
            goal.task_id = payload.get("task_id")
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal


@router.delete("/{goal_id}")
def delete_goal(goal_id: int) -> dict:
    with get_session() as session:
        goal = session.get(ProjectGoal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        session.delete(goal)
        session.commit()
    return {"status": "deleted", "goal_id": goal_id}
