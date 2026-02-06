from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.db.models import Artifact
from app.db.session import get_session

router = APIRouter()


@router.post("/", response_model=Artifact)
def create_artifact(artifact: Artifact) -> Artifact:
    with get_session() as session:
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        return artifact


@router.get("/", response_model=List[Artifact])
def list_artifacts() -> List[Artifact]:
    with get_session() as session:
        return list(session.exec(select(Artifact)))


@router.get("/{artifact_id}", response_model=Artifact)
def get_artifact(artifact_id: int) -> Artifact:
    with get_session() as session:
        artifact = session.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return artifact
