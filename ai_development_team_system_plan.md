# Overmind — System Design and Implementation Plan

## Overview

This document defines the architecture, data model, workflow, and implementation plan for the Overmind system. The system enables users to configure AI agents representing typical software development roles and orchestrates them to plan, implement, test, review, and release software autonomously.

The system supports multiple model providers (OpenAI, Anthropic, Groq, Gemini, etc.) and dynamically populates available models based on provided API keys.

---

# Goals

## Primary Objectives

- Enable fully autonomous AI-driven software development
- Support configurable team composition and roles
- Allow provider-agnostic model selection per agent
- Maintain persistent state and full auditability
- Execute deterministic, reproducible development runs
- Integrate directly with git repositories

## Secondary Objectives

- Provide real-time visibility into agent activities
- Allow replay and debugging of runs
- Support cost and token budget controls
- Enable extensibility for new providers and roles

---

# System Architecture

## Core Components

### 1. Orchestrator

Responsible for coordinating the entire development lifecycle.

Responsibilities:

- Run workflow pipelines
- Assign tasks to agents
- Track progress and state
- Enforce policies and permissions
- Handle retries and failures

Location:

```
app/core/orchestrator.py
```

---

### 2. Agent Runtime

Executes AI agents representing development roles.

Responsibilities:

- Load agent configuration
- Build prompts
- Call provider APIs
- Validate structured outputs
- Store artifacts

Location:

```
app/agents/runtime.py
```

---

### 3. Provider Adapter Layer

Abstracts model providers and enables dynamic model discovery.

Responsibilities:

- Validate API keys
- Fetch available models
- Normalize model metadata
- Execute inference requests

Location:

```
app/providers/
```

Example adapters:

```
openai_provider.py
anthropic_provider.py
groq_provider.py
gemini_provider.py
```

---

### 4. Model Registry

Caches and manages model metadata.

Responsibilities:

- Cache provider model lists
- Normalize model properties
- Provide filtered lists to UI

Location:

```
app/providers/model_registry.py
```

---

### 5. Repository Workspace Manager

Handles git operations and isolated execution environments.

Responsibilities:

- Clone repositories
- Create branches
- Apply patches
- Run tests
- Commit and merge

Location:

```
app/repo/workspace.py
```

---

### 6. Database Layer

Stores all system state.

Recommended initial backend:

- SQLite

Future option:

- PostgreSQL

Location:

```
app/db/
```

---

### 7. API Layer

Provides REST and WebSocket interfaces.

Framework:

- FastAPI

Location:

```
app/api/
```

---

### 8. User Interface

Provides configuration and monitoring tools.

Responsibilities:

- Project management
- Team configuration
- Run monitoring
- Artifact viewing

Location:

```
app/ui/
```

---

# Repository Structure

```
app/
  api/
  core/
  agents/
  providers/
  repo/
  db/
  ui/

models/
tests/
docs/
```

---

# Data Model

## Project

```
id
name
repo_url
repo_local_path
default_branch
overview
constraints
coding_standards
definition_of_done
created_at
```

---

## Team

```
id
project_id
name
template
created_at
```

---

## AgentConfig

```
id
team_id
role
provider
model
permissions
capabilities
created_at
```

Permissions example:

```
read_repo
write_repo
run_tests
create_pr
merge_pr
```

---

## Run

```
id
project_id
team_id
goal
status
start_time
end_time
token_usage
cost_estimate
```

---

## Task

```
id
run_id
title
description
acceptance_criteria
assigned_role
dependencies
status
created_at
completed_at
```

---

## Artifact

```
id
task_id
type
content
created_at
```

Artifact types:

- Plan
- Patch
- TestReport
- Review
- Decision
- Bug

---

# Agent Roles

## Product Owner

Responsibilities:

- Interpret project goals
- Create user stories
- Define priorities

---

## Delivery Manager

Responsibilities:

- Convert stories into tasks
- Assign tasks
- Manage dependencies

---

## Tech Lead

Responsibilities:

- Ensure architectural consistency
- Review technical decisions

---

## Developer

Responsibilities:

- Implement features
- Fix bugs
- Write tests

---

## QA Engineer

Responsibilities:

- Execute tests
- Identify defects
- Validate acceptance criteria

---

## Release Manager

Responsibilities:

- Merge changes
- Tag releases
- Generate release notes

---

# Workflow Pipeline

## Phase 1: Intake

Input:

- Project selection
- Team selection
- Goal

Output:

- Run created

---

## Phase 2: Planning

Agents:

- Product Owner
- Delivery Manager

Output:

- Backlog
- Tasks

---

## Phase 3: Execution

Agents:

- Developers

Output:

- Code patches

---

## Phase 4: Testing

Agents:

- QA

Output:

- Test reports

---

## Phase 5: Review

Agents:

- Tech Lead
- Manager

Output:

- Review artifacts

---

## Phase 6: Release

Agents:

- Release Manager

Output:

- Merge
- Tag
- Changelog

---

# Provider Integration

## Provider Interface

Required methods:

```
validate_key()
list_models()
invoke_model()
```

---

## Model Metadata Format

```
id
provider
supports_tools
supports_vision
context_length
recommended_roles
```

---

# Model Selection Workflow

1. User enters API key
2. System validates key
3. System fetches models
4. System caches models
5. UI updates role model dropdowns

---

# Workspace and Git Operations

Capabilities:

- Clone repository
- Create branch
- Apply patch
- Commit
- Merge
- Run tests

Isolation options:

- Local virtualenv
- Docker container

---

# Artifact System

All agent outputs must conform to structured schemas.

Example artifact structure:

```
{
  "type": "Patch",
  "summary": "Add login endpoint",
  "files": []
}
```

---

# Orchestrator Execution Loop

```
create_run()
plan()
execute_tasks()
run_tests()
review_changes()
release()
complete_run()
```

---

# Team Commands

- `@break`: pauses all agent work for the active run.
- `@attention`: pauses work and calls a team meeting.
- `@resume`: resumes work (any stakeholder message also resumes).

---

# Concurrency Control

Rules:

- One writer per file/module
- Multiple readers allowed

---

# Cost Controls

Configurable:

- Max tokens per task
- Max tokens per run
- Max retries

---

# API Endpoints

Examples:

```
POST /projects
GET /projects
POST /teams
GET /models
POST /runs
GET /runs
GET /tasks
GET /artifacts
```

---

# UI Pages

## Projects Page

- Create
- Select

## Team Builder

- Configure agents
- Select models

## Run Console

- Monitor progress
- View artifacts

## Settings

- Provider keys

---

# Implementation Phases

## Phase 1

- Database
- Schemas

## Phase 2

- Provider adapters

## Phase 3

- Agent runtime

## Phase 4

- Orchestrator

## Phase 5

- Git integration

## Phase 6

- Testing integration

## Phase 7

- UI

## Phase 8

- Hardening

---

# Security Considerations

- Secret isolation
- Permission enforcement
- Audit logging

---

# Extensibility

Supports:

- New providers
- New roles
- New workflows

---

# Summary

This system provides a complete architecture for fully automated AI-driven software development, with configurable teams, dynamic model selection, persistent state management, and deterministic orchestration.

It is designed to be scalable, auditable, and extensible.

---

End of Document

