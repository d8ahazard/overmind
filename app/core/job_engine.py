import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Dict, Iterable, Optional

from app.core.events import Event, EventBus
from sqlmodel import select

from app.db.models import Job, JobEvent, JobStep
from app.db.session import get_session


@dataclass
class JobStepResult:
    success: bool
    error: Optional[str] = None


class JobEngine:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def create_job(self, run_id: int) -> int:
        with get_session() as session:
            existing = session.exec(
                select(Job).where(Job.run_id == run_id)
            ).first()
            if existing:
                if existing.id is None:
                    raise RuntimeError("Job id not assigned")
                return existing.id
            job = Job(run_id=run_id, status="created", current_state="created")
            session.add(job)
            session.commit()
            session.refresh(job)
            if job.id is None:
                raise RuntimeError("Job id not assigned")
            return job.id

    async def run(
        self,
        job_id: int,
        steps: Iterable[str],
        handlers: Dict[str, Callable[[], Awaitable[JobStepResult]]],
        max_attempts: int = 2,
    ) -> None:
        for step_name in steps:
            step = self._start_step(job_id, step_name)
            await self._emit(job_id, "job.step.started", {"step": step_name, "job_id": job_id})
            result = await self._run_step_with_retries(step, handlers, max_attempts)
            if not result.success:
                self._fail_job(job_id, step, result.error or "step_failed")
                await self._emit(
                    job_id,
                    "job.failed",
                    {"step": step_name, "job_id": job_id, "error": result.error},
                )
                return
            self._complete_step(job_id, step)
            await self._emit(job_id, "job.step.completed", {"step": step_name, "job_id": job_id})

        self._complete_job(job_id)
        await self._emit(job_id, "job.completed", {"job_id": job_id})

    async def _run_step_with_retries(
        self,
        step: JobStep,
        handlers: Dict[str, Callable[[], Awaitable[JobStepResult]]],
        max_attempts: int,
    ) -> JobStepResult:
        handler = handlers.get(step.name)
        if not handler:
            return JobStepResult(False, "missing_handler")
        for attempt in range(1, max_attempts + 1):
            try:
                step.attempts = attempt
                self._update_step(step)
                result = await handler()
                if result.success:
                    return result
                if attempt < max_attempts:
                    await asyncio.sleep(min(2**attempt, 5))
            except Exception as exc:
                if attempt >= max_attempts:
                    return JobStepResult(False, str(exc))
                await asyncio.sleep(min(2**attempt, 5))
        return JobStepResult(False, "max_attempts_exceeded")

    def _start_step(self, job_id: int, name: str) -> JobStep:
        with get_session() as session:
            job = session.get(Job, job_id)
            if not job:
                raise RuntimeError("Job not found")
            job.status = "running"
            job.current_state = name
            job.updated_at = datetime.utcnow()
            step = JobStep(job_id=job.id, name=name, status="running", started_at=datetime.utcnow())
            session.add(job)
            session.add(step)
            session.commit()
            session.refresh(step)
            return step

    def _complete_step(self, job_id: int, step: JobStep) -> None:
        with get_session() as session:
            persisted = session.get(JobStep, step.id)
            if not persisted:
                return
            persisted.status = "completed"
            persisted.ended_at = datetime.utcnow()
            job = session.get(Job, job_id)
            if job:
                job.updated_at = datetime.utcnow()
            session.add(persisted)
            session.commit()

    def _fail_job(self, job_id: int, step: JobStep, error: str) -> None:
        with get_session() as session:
            persisted = session.get(JobStep, step.id)
            if persisted:
                persisted.status = "failed"
                persisted.error = error
                persisted.ended_at = datetime.utcnow()
                session.add(persisted)
            job = session.get(Job, job_id)
            if job:
                job.status = "failed"
                job.updated_at = datetime.utcnow()
                session.add(job)
            session.commit()

    def _complete_job(self, job_id: int) -> None:
        with get_session() as session:
            persisted = session.get(Job, job_id)
            if not persisted:
                return
            persisted.status = "completed"
            persisted.current_state = "done"
            persisted.updated_at = datetime.utcnow()
            session.add(persisted)
            session.commit()

    async def _emit(self, job_id: int, event_type: str, payload: dict) -> None:
        event = Event(type=event_type, payload=payload)
        with get_session() as session:
            session.add(
                JobEvent(
                    job_id=job_id,
                    step_id=payload.get("step_id"),
                    type=event_type,
                    payload=json.dumps(payload, ensure_ascii=True),
                )
            )
            session.commit()
        await self.event_bus.publish(event)

    def _update_step(self, step: JobStep) -> None:
        with get_session() as session:
            persisted = session.get(JobStep, step.id)
            if not persisted:
                return
            persisted.attempts = step.attempts
            session.add(persisted)
            session.commit()
