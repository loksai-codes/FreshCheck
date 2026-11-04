import math
from datetime import date

from .config import HALF_LIFE, WEIGHTS
from .models import Claim, Finding

AUTHORITY = {"OFFICIAL": 1.0, "NEWS": 0.7, "COMMUNITY": 0.4, "OTHER": 0.3}


def score(claim: Claim, finding: Finding, today: date | None = None) -> Finding:
    if not finding.evidence:
        finding.label, finding.score = "UNVERIFIABLE", None
        return finding
    verdict = {"MATCHES": 1.0, "PARTIALLY_MATCHES": 0.5, "CONTRADICTED": 0.0}.get(
        finding.verdict, 0.0
    )
    now = today or date.today()
    ages = [(now - e.published_date).days for e in finding.evidence if e.published_date]
    recency = (
        sum(
            math.exp(-math.log(2) * max(0, age) / HALF_LIFE[claim.volatility.value]) for age in ages
        )
        / len(ages)
        if ages
        else 0.45
    )
    authority = sum(AUTHORITY.get(e.source_type, 0.3) for e in finding.evidence) / len(
        finding.evidence
    )
    agreement = (
        1.0
        if finding.verdict == "MATCHES"
        else (0.35 if finding.verdict == "PARTIALLY_MATCHES" else 0.0)
    )
    parts = {"verdict": verdict, "authority": authority, "recency": recency, "agreement": agreement}
    finding.breakdown = parts
    finding.score = round(100 * sum(parts[k] * WEIGHTS[k] for k in parts), 1)
    finding.label = (
        "CURRENT" if finding.score >= 80 else "LIKELY_STALE" if finding.score >= 50 else "OUTDATED"
    )
    return finding
