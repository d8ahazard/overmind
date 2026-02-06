import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.db.models import AuditLog
from app.db.session import get_session


@dataclass
class AuditEntry:
    actor: str
    action: str
    decision: str
    tool_name: Optional[str] = None
    risk_level: Optional[str] = None
    request: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    run_id: Optional[int] = None
    job_id: Optional[int] = None
    created_at: str = datetime.utcnow().isoformat()


class AuditLogger:
    def log(self, entry: AuditEntry) -> None:
        record = AuditLog(
            run_id=entry.run_id,
            job_id=entry.job_id,
            actor=entry.actor,
            action=entry.action,
            tool_name=entry.tool_name,
            risk_level=entry.risk_level,
            decision=entry.decision,
            request=json.dumps(entry.request or {}, ensure_ascii=True),
            result=json.dumps(entry.result or {}, ensure_ascii=True),
        )
        with get_session() as session:
            session.add(record)
            session.commit()
