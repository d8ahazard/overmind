from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False


class PolicyEngine:
    def __init__(self, allow_high_risk: bool = False) -> None:
        self.allow_high_risk = allow_high_risk

    def evaluate(
        self,
        *,
        actor_scopes: Iterable[str],
        required_scopes: Iterable[str],
        risk_level: str,
        approved: bool,
    ) -> PolicyDecision:
        actor_set = {scope.strip() for scope in actor_scopes if scope and scope.strip()}
        required_set = {scope.strip() for scope in required_scopes if scope and scope.strip()}
        if required_set and not required_set.issubset(actor_set):
            return PolicyDecision(False, "missing_required_scopes")

        if risk_level.lower() in {"high", "critical"} and not self.allow_high_risk:
            if not approved:
                return PolicyDecision(False, "approval_required", requires_approval=True)

        return PolicyDecision(True, "allowed")
