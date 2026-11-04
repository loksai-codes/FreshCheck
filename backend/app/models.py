from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class ClaimType(StrEnum):
    PRICING = "PRICING"
    API_VERSION = "API_VERSION"
    REGULATION = "REGULATION"
    COMPANY_FACT = "COMPANY_FACT"
    OTHER = "OTHER"


class Volatility(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Claim(BaseModel):
    id: str
    text: str
    span_start: int
    span_end: int
    claim_type: ClaimType = ClaimType.OTHER
    entity: str
    attribute: str
    claimed_value: str
    claimed_as_of: date | None = None
    volatility: Volatility = Volatility.MEDIUM


class Evidence(BaseModel):
    url: str
    title: str
    quote: str
    published_date: date | None = None
    source_type: str = "OTHER"


class Finding(BaseModel):
    verdict: str = "NO_EVIDENCE"
    current_value: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    reasoning: str = "No usable evidence was available."
    value_valid_from: date | None = None
    score: float | None = None
    label: str = "UNVERIFIABLE"
    breakdown: dict[str, float] = Field(default_factory=dict)


class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    force: bool = False
