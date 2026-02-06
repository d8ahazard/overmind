import asyncio

from app.core.artifacts import ArtifactStore
from app.core.events import EventBus
from app.core.job_engine import JobEngine
from app.core.orchestrator import Orchestrator
from app.core.verification import NoopVerifier
from app.db.models import AgentConfig, Project, Run, Team
from app.db.session import init_db, get_session


class FakeRuntime:
    async def run_agent(self, run_id, agent, goal):
        return {"content": f"{agent.role} ack {goal}"}


def test_orchestrator_completes_run(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    init_db(db_url)
    with get_session() as session:
        project = Project(name="Test", repo_local_path=".")
        session.add(project)
        session.commit()
        session.refresh(project)
        team = Team(project_id=project.id, name="Team")
        session.add(team)
        session.commit()
        session.refresh(team)
        session.add(
            AgentConfig(
                team_id=team.id,
                role="Developer",
                provider="openai",
                model="gpt-4"
            )
        )
        run = Run(project_id=project.id, team_id=team.id, goal="Ship")
        session.add(run)
        session.commit()
        session.refresh(run)

    event_bus = EventBus()
    artifacts = ArtifactStore(tmp_path / "artifacts")
    orchestrator = Orchestrator(
        event_bus,
        artifacts,
        FakeRuntime(),
        tmp_path,
        JobEngine(event_bus),
        NoopVerifier(),
    )
    asyncio.run(orchestrator.start_run(run.id))

    with get_session() as session:
        updated = session.get(Run, run.id)
        assert updated.status == "completed"
