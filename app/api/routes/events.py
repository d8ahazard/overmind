from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.core.artifacts import ArtifactStore
from app.db.models import Run
from app.db.session import get_session

router = APIRouter()


@router.get("/history")
def events_history(request: Request, run_id: int | None = None) -> dict:
    with get_session() as session:
        run = session.get(Run, int(run_id)) if run_id else None
        if not run:
            active_project_id = request.app.state.active_project_id
            if active_project_id is None:
                raise HTTPException(status_code=404, detail="Active project not set")
            run = session.exec(
                select(Run)
                .where(Run.project_id == active_project_id)
                .order_by(Run.id.desc())
            ).first()
        if not run:
            return {"run_id": None, "events": []}
    store = ArtifactStore(request.app.state.data_dir)
    return {"run_id": run.id, "events": store.read_events(run.id)}
