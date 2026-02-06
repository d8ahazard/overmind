from fastapi import APIRouter, Request

from app.core.presets import build_agents, DEFAULT_PERSONALITIES
from app.db.models import PersonalityTemplate, Project, Run, Team
from app.db.session import get_session

router = APIRouter()


@router.post("/")
def seed_default(request: Request) -> dict:
    settings = request.app.state.settings
    registry = request.app.state.project_registry
    active = registry.get_active()
    with get_session() as session:
        if active:
            project = session.get(Project, active.id)
            if not project:
                project = Project(
                    id=active.id,
                    name=active.name,
                    repo_local_path=active.repo_local_path,
                )
                session.add(project)
                session.commit()
                session.refresh(project)
        else:
            project = Project(
                name="StandYourGround",
                repo_local_path=str(settings.default_project_root),
            )
            session.add(project)
            session.commit()
            session.refresh(project)

        team = Team(project_id=project.id, name="Core Team")
        session.add(team)
        session.commit()
        session.refresh(team)

        templates = [
            PersonalityTemplate(role=role, name=f"{role} default", script=script)
            for role, script in DEFAULT_PERSONALITIES.items()
        ]
        session.add_all(templates)
        session.commit()

        agents = build_agents(team.id, "medium", "openai", "gpt-4")
        session.add_all(agents)
        session.commit()

        run = Run(project_id=project.id, team_id=team.id, goal="Initial run")
        session.add(run)
        session.commit()
        session.refresh(run)

    return {
        "project_id": project.id,
        "team_id": team.id,
        "run_id": run.id,
    }
