"""
gates.py — handler functions backing the three Gate-related agent tools.

Adapted from your uploaded gates.py to call the real tools/chart.py
(get_natal_chart) rather than a standalone wealth_algorithm.py -- the tool
schemas and the shape of what each handler returns are unchanged from
what you specified. Registration into agent_loop.py's TOOLS list / dispatch
happens there, not here (matching this project's existing split: chart.py
/ scoring.py / calendar_bridge.py hold pure logic, agent_loop.py wires it
into the Anthropic tool-use loop).

House fields return None everywhere in this module. wealth_algorithm.py
(as uploaded) has no HOUSES table / house_of_sign() / house_for_longitude()
-- see tools/human_design_gates.py's module docstring. Once you upload the
real house-system file, get_chart_gates' per-body "house" and get_day_gate's
"house" both start populating with a one-line change each, flagged inline.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict

from . import gate_calendar_bridge as gcb
from . import human_design_gates as hdg
from .chart import get_natal_chart


def handle_get_gate_for_longitude(sidereal_longitude: float) -> Dict[str, Any]:
    return hdg.gate_for_longitude(sidereal_longitude)


def handle_get_chart_gates(
    birth_date: str,
    latitude: float,
    longitude: float,
    birth_time: str = "12:00:00",
    name: str = "Native",
) -> Dict[str, Any]:
    chart = get_natal_chart(birth_date, birth_time, latitude, longitude, sidereal=True)
    if chart.errors:
        # Non-fatal (matches the rest of this project's error-surfacing
        # pattern) -- a missing body/star doesn't block the Gates that did
        # compute; the caller sees exactly what failed.
        pass

    gate_info = hdg.bodies_to_gates(chart.positions)

    bodies = {}
    for body, g in gate_info.items():
        bi = chart.body_info.get(body, {})
        bodies[body] = {
            "constellation": bi.get("sign"),
            "deg_in_sign": bi.get("deg_in_sign"),
            "retro": bi.get("retro"),
            "house": None,  # TODO: wa.house_of_sign(bi.get("sign")) once that exists
            "gate": g["gate"],
            "line": g["line"],
            "element": g["element"],
            "symbol": g["symbol"],
            "z": g["z"],
            "hexagram_hanzi": g["hexagram_hanzi"],
            "hexagram_pinyin": g["hexagram_pinyin"],
        }

    return {
        "name": name,
        "datetime_utc": f"{birth_date}T{birth_time}",
        "mode": "sidereal_lahiri_13sign_64gate",
        "house_system_available": False,
        "bodies": bodies,
        "errors": chart.errors,
    }


def handle_get_day_gate(date: str = "") -> Dict[str, Any]:
    try:
        d = _dt.date.fromisoformat(date) if date else _dt.date.today()
    except ValueError as exc:
        return {"error": f"Date parse error: {exc}"}
    return gcb.day_gate(d)
