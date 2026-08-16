"""
gate_calendar_bridge.py — Day Gate computation + boost orchestration.

Adapted from your uploaded gate_calendar_bridge.py to call the real
tools/chart.py and tools/calendar_bridge.py rather than a standalone
wealth_algorithm.py -- the underlying logic (Day Gate = the Gate the Sun
sidereally occupies on a civil date) is unchanged.

Concept -- "Day Gate": distinct in kind from the other two boost tiers.
Month-ruler and suit-element both compare a chart against ITS OWN birth
date's cosmic-calendar position. Day Gate instead compares a chart against
the Sun's CURRENTLY TRANSITING Gate -- "is this chart in resonance with
today" rather than "is this chart in resonance with its own birth
circumstances." A body in the chart whose own Gate matches today's Day
Gate earns the boost. Boost size: BOOST_DAY_GATE = 1.15 (calendar_bridge.py).

House: day_gate() cannot report the Sun's House right now.
wealth_algorithm.py (as uploaded) has no house_for_longitude() -- see
tools/human_design_gates.py's module docstring for the same gap. Returns
"house": None with a note rather than fabricating one.
"""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

from . import calendar_bridge as cb
from . import human_design_gates as hdg
from .chart import calc_planets, get_julian_day, setup_ephemeris


def day_gate(greg_date: _dt.date, hour: int = 12) -> dict:
    """The Gate (+ Line) the Sun sidereally occupies on a civil date, with
    that date's cosmic_calendar card attached for context. `hour` sets the
    UTC hour used for the Sun position (default noon -- the Sun moves <1deg
    across a day, far less than a 5.625deg gate width, so this barely
    matters except right at a gate-boundary crossing)."""
    setup_ephemeris()
    jd = get_julian_day(greg_date.year, greg_date.month, greg_date.day, float(hour))
    lons, _retro, errors = calc_planets(jd, sidereal=True)

    if "Sun" not in lons:
        return {"error": f"Could not compute Sun position for {greg_date.isoformat()}: {errors}"}

    sun_gate = hdg.gate_for_longitude(lons["Sun"])
    cosmic_info = cb.date_to_cosmic_raw(greg_date)
    card = cosmic_info["card"] if cosmic_info else None

    return {
        "date": greg_date.isoformat(),
        "sun_sid_lon": sun_gate["sid_lon"],
        "house": None,  # wealth_algorithm.py has no house system yet -- see module docstring
        "gate": sun_gate["gate"],
        "line": sun_gate["line"],
        "element": sun_gate["element"],
        "symbol": sun_gate["symbol"],
        "hexagram_hanzi": sun_gate["hexagram_hanzi"],
        "hexagram_pinyin": sun_gate["hexagram_pinyin"],
        "card": card,  # (suit_symbol, value) or None (Leap Day edge case)
        "card_display": cb.card_str(card) if card else None,
    }


def gate_boost_weights(
    chart_gate_info: Dict[str, dict],
    greg_date: _dt.date,
    boost: float = 1.15,
    hour: int = 12,
) -> Dict[str, float]:
    """{body: multiplier} -- `boost` where a body's own Gate matches the
    day's Sun-Gate, else 1.0. `chart_gate_info` is exactly what
    human_design_gates.bodies_to_gates() returns."""
    today = day_gate(greg_date, hour=hour)
    if "error" in today:
        return {body: 1.0 for body in chart_gate_info}
    today_gate = today["gate"]
    return {
        body: (boost if g["gate"] == today_gate else 1.0)
        for body, g in chart_gate_info.items()
    }


def apply_all_cosmic_boosts(
    score_dict: dict,
    lons: Dict[str, float],
    birth_greg_date: _dt.date,
    as_of_date: Optional[_dt.date] = None,
    hour: int = 12,
) -> dict:
    """One-call version of calendar_bridge.apply_cosmic_boosts() that also
    supplies the day-gate tier. cosmic_info (month ruler / suit element)
    is evaluated at `birth_greg_date` (the chart's own birth date, matching
    the other two tiers); the day-gate tier is evaluated at `as_of_date`
    (defaults to today) since it's a transit comparison, not a birth-data
    comparison -- see module docstring.

    Uses calendar_bridge.date_to_cosmic_day() (the public, label-based,
    JSON-safe wrapper) rather than date_to_cosmic_raw() -- the raw form
    carries a live datetime.date under 'greg' that isn't JSON-serializable,
    which would otherwise break the tool_result payload the agent loop
    sends back to the API."""
    cosmic_info = cb.date_to_cosmic_day(birth_greg_date.isoformat())
    if "error" in cosmic_info:
        raise ValueError(f"No cosmic position for {birth_greg_date}: {cosmic_info['error']}")

    gate_info = hdg.bodies_to_gates(lons)
    today = day_gate(as_of_date or _dt.date.today(), hour=hour)
    today_gate = today.get("gate")

    return cb.apply_cosmic_boosts(
        score_dict, cosmic_info, gate_info=gate_info, day_gate=today_gate
    )
