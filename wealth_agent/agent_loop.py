"""
agent_loop.py — Tool-calling loop against the Anthropic API for the
wealth scoring agent.

FRAMEWORK NOTE: your uploaded wealth_algorithm.py defaults to TROPICAL
and takes --sidereal to opt in. Per your standing instruction for this
project, get_natal_chart is ALWAYS called with sidereal=True here --
never exposed as a choice to the model. The system prompt below
reinforces this in the model's own language too.

Tracked bodies (matching your source exactly): Sun, Moon, Mercury, Venus,
Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, True Black Moon Lilith (11
"planets") + Lot of Fortune, Lot of Spirit, White Moon Selena (3 computed
points), plus 18 fixed stars. Chiron is NOT a tracked/scored body -- see
calendar_bridge.py's COSMIC_MONTH_RULERS note for how Ophiuchus's
traditional-ruler label is handled.

Run from inside the wealth_agent/ directory: `python agent_loop.py`
Requires: ANTHROPIC_API_KEY environment variable set to a real key.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import anthropic

from tools.chart import (
    get_natal_chart, chart_to_dict, NatalChart,
    PLANET_CATALOG, COMPUTED_WEIGHTS,
)
from tools.scoring import score_wealth, score_result_to_dict
from tools.calendar_bridge import (
    cosmic_day_to_date,
    date_to_cosmic_day,
    apply_cosmic_boosts,
)
from cache import ChartCache

MODEL = "claude-sonnet-5"
MAX_TOKENS = 2048
MAX_TOOL_ITERATIONS = 8  # safety valve against runaway tool-call loops

SYSTEM_PROMPT = """You are a wealth-scoring astrology agent built on the user's \
own wealth_algorithm.py and cosmic_calendar.py. Operate strictly under TRUE \
SIDEREAL astrology -- Lahiri ayanamsa, 13-sign zodiac including Ophiuchus \
-- per the Capricorn Prometheus Software framework. Never describe \
placements in tropical terms.

Tracked bodies: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, \
Neptune, Pluto, True Black Moon Lilith, Lot of Fortune, Lot of Spirit, \
White Moon Selena, plus 18 fixed stars. Chiron is NOT a tracked body here \
-- it only labels Ophiuchus's traditional rulership. Don't claim a Chiron \
position exists or was computed.

Custom rulerships: Venus rules Virgo, Mercury rules Libra (in addition to \
their traditional signs). Aspects include three metallic-ratio angles \
(Golden, Silver, Bronze) alongside the standard set -- a single pair of \
bodies CAN trigger more than one aspect simultaneously if orbs overlap; \
that's expected, not a bug to paper over.

Always call get_natal_chart before score_wealth for a new person -- \
score_wealth reads the previously stored chart by label rather than \
taking birth data directly. Use recall_chart / list_recalled_charts when \
a user references someone already computed this session.

The final normalized_score (0-100) comes with a rating label (Exceptional \
/ Strong / Moderate / Developing / Challenging) -- use it, don't invent \
your own tier language. After tool results come back, always finish with \
a short plain-language interpretation -- never leave raw JSON as the \
final answer, and don't dump the entire aspect_log; mention only the \
handful of strongest contributors (already sorted by |contrib| descending).

If a tool result contains an "errors" or "error" field, name the specific \
issue in your reply instead of glossing over it or inventing a value to \
fill the gap."""

TOOLS = [
    {
        "name": "get_natal_chart",
        "description": (
            "Compute a true sidereal (Lahiri) natal chart -- all 11 "
            "tracked planets/points, 3 computed points (Lots + Selena), "
            "18 fixed stars, ascendant, and day/night status -- and store "
            "it under a label for later recall. Always call this before "
            "score_wealth for a new person."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "birth_date": {"type": "string", "description": "YYYY-MM-DD"},
                "birth_time": {"type": "string", "description": "HH:MM or HH:MM:SS, 24hr, in UT"},
                "latitude": {"type": "number", "description": "N positive, S negative"},
                "longitude": {"type": "number", "description": "E positive, W negative"},
                "label": {
                    "type": "string",
                    "description": "Short handle to recall this chart later, e.g. 'self' or 'partner'.",
                },
            },
            "required": ["birth_date", "birth_time", "latitude", "longitude", "label"],
        },
    },
    {
        "name": "score_wealth",
        "description": (
            "Compute the normalized 0-100 wealth score (+ rating label) "
            "for a previously computed chart (by label): planet-planet and "
            "planet-star aspects (14 types incl. metallic-ratio angles), "
            "dignity/debility bonuses, and automatic Cosmic Calendar "
            "month-ruler / suit-element boosts based on the chart's birth date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Label used in get_natal_chart"},
            },
            "required": ["label"],
        },
    },
    {
        "name": "cosmic_day_to_date",
        "description": "Forward lookup: cosmic (year label, month 1-13, day 1-28) -> Gregorian date + playing card.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cosmic_year": {"type": "integer", "description": "Cosmic year LABEL, e.g. 2026 = Dec 2025 - Dec 2026"},
                "month": {"type": "integer", "description": "1-13"},
                "day_in_month": {"type": "integer", "description": "1-28"},
            },
            "required": ["cosmic_year", "month", "day_in_month"],
        },
    },
    {
        "name": "date_to_cosmic_day",
        "description": (
            "Reverse lookup: Gregorian date -> cosmic year/month/day + "
            "playing card. Correctly handles the Leap/Joker Day (Dec 18) "
            "and the intercalary Feb 29 (7 of Diamonds) as explicit cases."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gregorian_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["gregorian_date"],
        },
    },
    {
        "name": "recall_chart",
        "description": "Retrieve a previously computed chart by label without recomputing it.",
        "input_schema": {
            "type": "object",
            "properties": {"label": {"type": "string"}},
            "required": ["label"],
        },
    },
    {
        "name": "list_recalled_charts",
        "description": "List labels of all charts computed so far this session.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_ALL_WEIGHTS: Dict[str, int] = {n: d["weight"] for n, d in PLANET_CATALOG.items()}
_ALL_WEIGHTS.update(COMPUTED_WEIGHTS)


class SessionState:
    """Holds charts computed during this conversation, keyed by label.
    Lives only in memory -- separate from ChartCache, which persists raw
    ephemeris results to disk across process runs."""

    def __init__(self):
        self.charts: Dict[str, dict] = {}

    def store(self, label: str, chart_dict: dict) -> None:
        self.charts[label] = chart_dict

    def get(self, label: str) -> Optional[dict]:
        return self.charts.get(label)


def _rebuild_natal_chart(chart_dict: dict) -> NatalChart:
    """Reconstruct a scoring-ready NatalChart from a serialized chart_dict
    (chart_to_dict() output, as stored in SessionState/ChartCache).
    Weights aren't part of the serialized form (they're static catalog
    data, not per-chart) so they're rebuilt from PLANET_CATALOG/
    COMPUTED_WEIGHTS directly rather than round-tripped."""
    positions = {name: info["lon"] for name, info in chart_dict["bodies"].items()}
    nc = NatalChart(
        birth_date=chart_dict["birth_date"], birth_time=chart_dict["birth_time"],
        latitude=chart_dict["latitude"], longitude=chart_dict["longitude"],
        julian_day=0.0,  # not needed downstream; scoring reads positions/body_info only
        sidereal=chart_dict["sidereal"],
        ascendant=chart_dict["ascendant"], is_day=chart_dict["is_day_chart"],
        positions=positions, weights=dict(_ALL_WEIGHTS),
        body_info=chart_dict["bodies"],
        star_positions=chart_dict["fixed_stars"],
        errors=list(chart_dict.get("errors", [])),
    )
    return nc


class WealthAgent:
    def __init__(self, api_key: Optional[str] = None, cache: Optional[ChartCache] = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.session = SessionState()
        self.cache = cache or ChartCache()
        self.history: list[Dict[str, Any]] = []

    # -- tool dispatch --------------------------------------------------------
    def _dispatch(self, tool_name: str, tool_input: dict) -> dict:
        """Every branch returns a plain dict; every failure is caught and
        turned into {"error": ...} rather than raised, so a broken tool
        call surfaces to the model as data it can explain, not a crash."""
        try:
            if tool_name == "get_natal_chart":
                bd, bt = tool_input["birth_date"], tool_input["birth_time"]
                lat, lon = tool_input["latitude"], tool_input["longitude"]
                label = tool_input["label"]

                cached = self.cache.get(bd, bt, lat, lon)
                if cached is not None:
                    chart_dict = cached
                else:
                    chart = get_natal_chart(bd, bt, lat, lon, sidereal=True)  # always sidereal
                    chart_dict = chart_to_dict(chart)
                    self.cache.set(bd, bt, lat, lon, chart_dict)

                self.session.store(label, chart_dict)
                return chart_dict

            elif tool_name == "score_wealth":
                label = tool_input["label"]
                chart_dict = self.session.get(label)
                if chart_dict is None:
                    return {"error": f"No chart stored under label '{label}'. "
                                      f"Call get_natal_chart first."}
                nc = _rebuild_natal_chart(chart_dict)
                result_dict = score_result_to_dict(score_wealth(nc))
                cosmic_info = date_to_cosmic_day(chart_dict["birth_date"])
                return apply_cosmic_boosts(result_dict, cosmic_info)

            elif tool_name == "cosmic_day_to_date":
                return cosmic_day_to_date(
                    tool_input["cosmic_year"], tool_input["month"], tool_input["day_in_month"]
                )

            elif tool_name == "date_to_cosmic_day":
                return date_to_cosmic_day(tool_input["gregorian_date"])

            elif tool_name == "recall_chart":
                label = tool_input["label"]
                chart_dict = self.session.get(label)
                if chart_dict is None:
                    return {"error": f"No chart stored under label '{label}'"}
                return chart_dict

            elif tool_name == "list_recalled_charts":
                return {"labels": list(self.session.charts.keys())}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    # -- main loop --------------------------------------------------------------
    def send(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.history,
            )

            self.history.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return "".join(
                    block.text for block in response.content if block.type == "text"
                )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._dispatch(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            self.history.append({"role": "user", "content": tool_results})

        return ("[Stopped after reaching the tool-call safety limit -- the "
                "agent may be stuck in a loop. Check the conversation above.]")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "Set ANTHROPIC_API_KEY before running, e.g.:\n"
            "  $env:ANTHROPIC_API_KEY = 'your-key-here'   (current PowerShell session)\n"
            "  setx ANTHROPIC_API_KEY 'your-key-here'      (persists for new sessions)"
        )

    agent = WealthAgent()
    print("Wealth Agent -- true sidereal / Capricorn Prometheus framework.")
    print("Ctrl+C to exit.\n")
    while True:
        try:
            user_input = input("you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        if not user_input:
            continue
        reply = agent.send(user_input)
        print(f"\nagent> {reply}\n")