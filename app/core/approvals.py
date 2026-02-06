from typing import Optional

from app.db.models import Approval
from app.db.session import get_session


class ApprovalStore:
    def is_approved(self, approval_id: Optional[int]) -> bool:
        if not approval_id:
            return False
        with get_session() as session:
            approval = session.get(Approval, approval_id)
            if not approval:
                return False
            return approval.status.lower() == "approved"
