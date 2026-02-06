from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.db.models import Approval
from app.db.session import get_session

router = APIRouter()


@router.post("/", response_model=Approval)
def create_approval(approval: Approval) -> Approval:
    with get_session() as session:
        session.add(approval)
        session.commit()
        session.refresh(approval)
        return approval


@router.get("/", response_model=List[Approval])
def list_approvals() -> List[Approval]:
    with get_session() as session:
        return list(session.exec(select(Approval)))


@router.get("/{approval_id}", response_model=Approval)
def get_approval(approval_id: int) -> Approval:
    with get_session() as session:
        approval = session.get(Approval, approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        return approval


@router.patch("/{approval_id}", response_model=Approval)
def update_approval(approval_id: int, payload: dict) -> Approval:
    status = payload.get("status")
    actor = payload.get("actor")
    reason = payload.get("reason")
    with get_session() as session:
        approval = session.get(Approval, approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if status:
            approval.status = status
        if actor:
            approval.actor = actor
        if reason is not None:
            approval.reason = reason
        session.add(approval)
        session.commit()
        session.refresh(approval)
        return approval
