from typing import Optional

from app.db.models import Approval
from app.db.session import get_session


class ApprovalStore:
    def is_approved(
        self,
        approval_id: Optional[int],
        tool_name: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> bool:
        if not approval_id:
            return False
        with get_session() as session:
            approval = session.get(Approval, approval_id)
            if not approval:
                return False
            if approval.status.lower() != "approved":
                return False
            if tool_name and approval.tool_name and approval.tool_name != tool_name:
                return False
            if risk_level and approval.risk_level and approval.risk_level != risk_level:
                return False
            return True
