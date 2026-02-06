from dataclasses import dataclass
from typing import Optional


@dataclass
class VerificationResult:
    success: bool
    details: Optional[str] = None


class Verifier:
    async def verify(self, run_id: int, job_id: int) -> VerificationResult:
        return VerificationResult(True, "noop")


class NoopVerifier(Verifier):
    async def verify(self, run_id: int, job_id: int) -> VerificationResult:
        return VerificationResult(True, "noop")
