from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.db.models import (
    AgentMemory,
    Approval,
    AuditLog,
    Job,
    JobEvent,
    ProjectBudget,
    ProjectGoal,
    Run,
    Task,
)
from app.db.session import get_session

router = APIRouter()


@router.get("/summary")
def metrics_summary(
    request: Request, scope: str = "project", run_id: Optional[int] = None
) -> dict:
    project_id = request.app.state.active_project_id
    if project_id is None:
        raise HTTPException(status_code=404, detail="No active project")

    with get_session() as session:
        run_ids = []
        if run_id:
            run_ids = [run_id]
        else:
            run_ids = [
                item.id
                for item in session.exec(select(Run).where(Run.project_id == project_id))
            ]

        tasks_query = select(Task)
        runs_query = select(Run)
        if run_id:
            runs_query = runs_query.where(Run.id == run_id)
            tasks_query = tasks_query.where(Task.run_id == run_id)
        else:
            runs_query = runs_query.where(Run.project_id == project_id)
            if run_ids:
                tasks_query = tasks_query.where(Task.run_id.in_(run_ids))

        runs = list(session.exec(runs_query))
        tasks = list(session.exec(tasks_query))

        audit_query = select(AuditLog)
        if run_ids:
            audit_query = audit_query.where(AuditLog.run_id.in_(run_ids))
        audits = list(session.exec(audit_query))

        approvals_query = select(Approval)
        if run_ids:
            approvals_query = approvals_query.where(Approval.run_id.in_(run_ids))
        approvals = list(session.exec(approvals_query))

        memory_query = select(AgentMemory)
        if run_ids:
            memory_query = memory_query.where(AgentMemory.run_id.in_(run_ids))
        memories = list(session.exec(memory_query))

        jobs_query = select(Job)
        if run_ids:
            jobs_query = jobs_query.where(Job.run_id.in_(run_ids))
        jobs = list(session.exec(jobs_query))
        job_ids = [job.id for job in jobs if job.id]
        events_query = select(JobEvent)
        if job_ids:
            events_query = events_query.where(JobEvent.job_id.in_(job_ids))
        events = list(session.exec(events_query))

        goals_query = select(ProjectGoal).where(ProjectGoal.project_id == project_id)
        goals = list(session.exec(goals_query))

        budget = session.exec(
            select(ProjectBudget).where(ProjectBudget.project_id == project_id)
        ).first()

    tool_calls = [entry for entry in audits if entry.action == "tool.request"]
    tool_errors = [entry for entry in audits if entry.decision != "allowed"]
    tool_breakdown = {}
    for entry in tool_calls:
        name = entry.tool_name or "unknown"
        tool_breakdown[name] = tool_breakdown.get(name, 0) + 1

    goal_counts = {}
    for goal in goals:
        goal_counts[goal.status] = goal_counts.get(goal.status, 0) + 1

    return {
        "scope": scope,
        "run_id": run_id,
        "runs": len(runs),
        "tasks": len(tasks),
        "tool_calls": len(tool_calls),
        "tool_errors": len(tool_errors),
        "tool_breakdown": tool_breakdown,
        "approvals_pending": len([a for a in approvals if a.status == "pending"]),
        "memory_entries": len(memories),
        "events": len(events),
        "goals": goal_counts,
        "budget": {
            "usd_spent": budget.usd_spent if budget else 0,
            "usd_limit": budget.usd_limit if budget else 0,
        },
    }
