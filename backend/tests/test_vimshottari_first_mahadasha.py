import pytest
from datetime import datetime, timezone

from app.astro.dasha import calculate_vimshottari_timeline, DASHA_YEARS, DAYS_PER_YEAR


def test_first_mahadasha_balance_carries_into_antardasha():
    """
    For a Moon placed part-way through the starting nakshatra, the first
    Mahadasha is a remainder-only segment. The *first* Antardasha within this
    Mahadasha should reflect the carried-forward balance, i.e. it should not
    always be of the same lord as the Mahadasha itself.
    """
    # Use a synthetic birth where we control the Moon's nakshatra fraction.
    birth_utc = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Put Moon 20% into the first nakshatra (Ashwini). This gives:
    #   nak_idx0 = 0 (Ketu Mahadasha)
    #   frac = 0.2  (20% of Ketu Mahadasha already elapsed before birth)
    nakshatra_span_deg = 360.0 / 27.0
    moon_longitude_sidereal = 0.2 * nakshatra_span_deg

    timeline, _ = calculate_vimshottari_timeline(
        birth_utc=birth_utc,
        moon_longitude_sidereal=moon_longitude_sidereal,
        depth=2,
    )

    # First Mahadasha
    first_maha = timeline[0]
    assert first_maha["lord"] == "Ketu"
    assert "antardasha" in first_maha
    antars = first_maha["antardasha"]
    assert len(antars) > 0

    first_antar = antars[0]

    # With 20% of Ketu Mahadasha already elapsed, the running Antardasha at
    # birth should *not* be Ketu/Ketu. It should fall into the Venus Antardasha
    # segment of the Ketu Mahadasha.
    assert first_antar["lord"] == "Venus"

    # Additionally, ensure that the Antardashas of the first Mahadasha exactly
    # cover the remaining Mahadasha duration (within numerical tolerance).
    from_iso = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))

    maha_start = from_iso(first_maha["start"])
    maha_end = from_iso(first_maha["end"])
    maha_days = (maha_end - maha_start).total_seconds() / 86400.0

    total_antar_days = sum(a["durationDays"] for a in antars)

    assert total_antar_days == pytest.approx(maha_days, rel=1e-8, abs=1e-6)


