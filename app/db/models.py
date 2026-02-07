from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from pydantic import ConfigDict


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    repo_url: Optional[str] = None
    repo_local_path: str
    default_branch: Optional[str] = None
    team_framework: Optional[str] = None
    overview: Optional[str] = None
    constraints: Optional[str] = None
    coding_standards: Optional[str] = None
    definition_of_done: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectSetting(SQLModel, table=True):
    model_config = ConfigDict(protected_namespaces=())
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    allow_all_tools: bool = False
    allow_high_risk: bool = False
    default_tool_scopes: Optional[str] = None
    role_tool_scopes: Optional[str] = None
    allow_pm_merge: bool = False
    auto_execute_edits: bool = True
    require_pm_pr_approval: bool = True
    chat_target_policy: str = "managers"
    task_retry_limit: int = 3
    model_defaults: Optional[str] = None
    memory_profiles: Optional[str] = None
    mcp_endpoints: Optional[str] = None
    mcp_ports: Optional[str] = None
    enabled_plugins: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    name: str
    template: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    display_name: Optional[str] = None
    role: str
    gender: Optional[str] = None
    pronouns: Optional[str] = None
    personality: Optional[str] = None
    avatar_url: Optional[str] = None
    memory_summary: Optional[str] = None
    provider: str
    model: str
    permissions: Optional[str] = None
    capabilities: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    team_id: int = Field(foreign_key="team.id")
    goal: str
    status: str = "created"
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    token_usage: Optional[int] = None
    cost_estimate: Optional[float] = None
    pause_mode: Optional[str] = None
    pause_by: Optional[str] = None
    pause_at: Optional[datetime] = None


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    title: str
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    assigned_role: Optional[str] = None
    dependencies: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    attempts: int = 0


class Artifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    type: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentMemory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    agent_id: int = Field(foreign_key="agentconfig.id")
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PersonalityTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role: str
    name: str
    script: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str
    encrypted_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectBudget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    usd_limit: float
    usd_spent: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderBalance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str
    balance_usd: Optional[float] = None
    last_updated: Optional[datetime] = None


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    status: str = "created"
    current_state: str = "created"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    name: str
    status: str = "pending"
    attempts: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error: Optional[str] = None


class JobEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    step_id: Optional[int] = Field(default=None, foreign_key="jobstep.id")
    type: str
    payload: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: Optional[int] = Field(default=None, foreign_key="run.id")
    job_id: Optional[int] = Field(default=None, foreign_key="job.id")
    actor: str
    action: str
    tool_name: Optional[str] = None
    risk_level: Optional[str] = None
    decision: str
    request: Optional[str] = None
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Approval(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: Optional[int] = Field(default=None, foreign_key="run.id")
    job_id: Optional[int] = Field(default=None, foreign_key="job.id")
    actor: str
    tool_name: Optional[str] = None
    risk_level: Optional[str] = None
    status: str = "pending"
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)