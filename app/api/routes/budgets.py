from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.db.models import ProjectBudget, ProviderBalance
from app.db.session import get_session

router = APIRouter()


@router.get("/", response_model=List[ProjectBudget])
def list_budgets() -> List[ProjectBudget]:
    with get_session() as session:
        return list(session.exec(select(ProjectBudget)))


@router.post("/")
def set_budget(payload: dict, request: Request) -> ProjectBudget:
    project_id = payload.get("project_id") or request.app.state.active_project_id
    usd_limit = payload.get("usd_limit")
    if project_id is None or usd_limit is None:
        raise HTTPException(status_code=400, detail="project_id and usd_limit required")
    with get_session() as session:
        existing = session.exec(
            select(ProjectBudget).where(ProjectBudget.project_id == project_id)
        ).first()
        if existing:
            existing.usd_limit = float(usd_limit)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        budget = ProjectBudget(project_id=project_id, usd_limit=float(usd_limit))
        session.add(budget)
        session.commit()
        session.refresh(budget)
        return budget


@router.get("/balances", response_model=List[ProviderBalance])
def list_balances() -> List[ProviderBalance]:
    with get_session() as session:
        return list(session.exec(select(ProviderBalance)))


@router.post("/balances")
def upsert_balance(payload: dict) -> ProviderBalance:
    provider = payload.get("provider")
    balance = payload.get("balance_usd")
    if not provider:
        raise HTTPException(status_code=400, detail="provider required")
    with get_session() as session:
        existing = session.exec(
            select(ProviderBalance).where(ProviderBalance.provider == provider)
        ).first()
        if existing:
            existing.balance_usd = balance
            existing.last_updated = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        entry = ProviderBalance(
            provider=provider,
            balance_usd=balance,
            last_updated=datetime.utcnow(),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry
