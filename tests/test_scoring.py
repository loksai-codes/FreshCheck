from datetime import date

import pytest
from app.models import Claim, ClaimType, Evidence, Finding, Volatility
from app.scoring import score


@pytest.mark.parametrize(
    "verdict,authority,label",
    [
        ("MATCHES", "OFFICIAL", "CURRENT"),
        ("PARTIALLY_MATCHES", "OTHER", "LIKELY_STALE"),
        ("CONTRADICTED", "OTHER", "OUTDATED"),
    ],
)
def test_score_table(verdict, authority, label):
    c = Claim(
        id="1",
        text="API v2",
        span_start=0,
        span_end=6,
        entity="API",
        attribute="version",
        claimed_value="v2",
        claim_type=ClaimType.API_VERSION,
        volatility=Volatility.MEDIUM,
    )
    e = Evidence(
        url="https://example.test",
        title="Source",
        quote="Version 2 is current",
        source_type=authority,
        published_date=date.today(),
    )
    result = score(c, Finding(verdict=verdict, evidence=[e]), today=date.today())
    assert result.label == label


def test_no_evidence_is_unverifiable():
    c = Claim(
        id="1",
        text="x",
        span_start=0,
        span_end=1,
        entity="x",
        attribute="y",
        claimed_value="z",
    )
    assert score(c, Finding()).label == "UNVERIFIABLE"
