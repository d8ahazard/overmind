from dataclasses import dataclass
from typing import Protocol


@dataclass
class ConnectorStatus:
    name: str
    available: bool
    detail: str | None = None


class GitConnector(Protocol):
    name: str

    async def create_branch(self, repo: str, branch: str, base: str) -> ConnectorStatus:
        ...

    async def create_pull_request(self, repo: str, title: str, body: str, head: str, base: str) -> ConnectorStatus:
        ...


class IssueTrackerConnector(Protocol):
    name: str

    async def create_ticket(self, project: str, title: str, body: str) -> ConnectorStatus:
        ...


class NotificationConnector(Protocol):
    name: str

    async def send(self, channel: str, message: str) -> ConnectorStatus:
        ...


class NoopGitConnector:
    name = "noop-git"

    async def create_branch(self, repo: str, branch: str, base: str) -> ConnectorStatus:
        return ConnectorStatus(name=self.name, available=False, detail="not_configured")

    async def create_pull_request(self, repo: str, title: str, body: str, head: str, base: str) -> ConnectorStatus:
        return ConnectorStatus(name=self.name, available=False, detail="not_configured")


class NoopIssueConnector:
    name = "noop-issues"

    async def create_ticket(self, project: str, title: str, body: str) -> ConnectorStatus:
        return ConnectorStatus(name=self.name, available=False, detail="not_configured")


class NoopNotificationConnector:
    name = "noop-notify"

    async def send(self, channel: str, message: str) -> ConnectorStatus:
        return ConnectorStatus(name=self.name, available=False, detail="not_configured")
