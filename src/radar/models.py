"""Strict, explicit data types for the radar; no fake safety ratings."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

class CheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    HARD_REJECT = "HARD_REJECT"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class SecurityDecision(str, Enum):
    REJECT_SECURITY = "REJECT_SECURITY"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"
    WATCHLIST = "WATCHLIST"
    ELIGIBLE_PASS = "ELIGIBLE_PASS"

@dataclass(frozen=True)
class Candidate:
    mint: str
    pool: str
    dex: str
    created_at: datetime
    observed_at: datetime
    liquidity_usd: Decimal | None
    volume_5m_usd: Decimal | None
    volume_1h_usd: Decimal | None
    buys_5m: int | None
    sells_5m: int | None
    trades_1h: int | None
    price_change_1h_pct: Decimal | None
    source: str = "geckoterminal"

    @property
    def age_minutes(self) -> float:
        return (self.observed_at - self.created_at).total_seconds() / 60

@dataclass(frozen=True)
class RuleCheck:
    code: str
    status: CheckStatus
    explanation: str
    source: str

@dataclass(frozen=True)
class SecurityEvaluation:
    mint: str
    decision: SecurityDecision
    checks: tuple[RuleCheck, ...]
    risk_score: int | None = None
    data_coverage_pct: float | None = None
    mandatory_complete: bool = False
