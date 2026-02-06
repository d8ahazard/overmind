from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.db.models import PersonalityTemplate
from app.db.session import get_session

router = APIRouter()


@router.post("/", response_model=PersonalityTemplate)
def create_template(template: PersonalityTemplate) -> PersonalityTemplate:
    with get_session() as session:
        session.add(template)
        session.commit()
        session.refresh(template)
        return template


@router.get("/", response_model=List[PersonalityTemplate])
def list_templates() -> List[PersonalityTemplate]:
    with get_session() as session:
        return list(session.exec(select(PersonalityTemplate)))


@router.delete("/{template_id}")
def delete_template(template_id: int) -> dict:
    with get_session() as session:
        template = session.get(PersonalityTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        session.delete(template)
        session.commit()
        return {"status": "deleted", "template_id": template_id}
