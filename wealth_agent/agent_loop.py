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
points), plus 30 fixed stars/deep-space points. Chiron is NOT a tracked/scored body -- see
calendar_bridge.py's COSMIC_MONTH_RULERS note for how Ophiuchus's
traditional-ruler label is handled.

64-GATE HUMAN DESIGN LAYER: three more tools (get_gate_for_longitude,
get_chart_gates, get_day_gate) overlay the I Ching/periodic-table gate
wheel on the same sidereal ring, and score_wealth's boost pipeline gained
a third tier (day-gate resonance, x1.15) alongside the existing
month-ruler and suit-element boosts. HOUSE FIELDS ARE CURRENTLY None
EVERYWHERE: the uploaded wealth_algorithm.py has no house system despite
one being described in an accompanying README -- see tools/gates.py's
module docstring for exactly what to fix once the real file arrives.

TYPOLOGY LAYER (Enneagram + MBTI): get_natal_chart takes two more optional
fields (enneagram_type, mbti_type) -- GIVEN/self-reported, never computed,
same as birth data itself. score_wealth's boost pipeline gained a fourth
tier (typology resonance) that fires only when at least one was provided.
See tools/typology.py's module docstring for real data-quality caveats in
the source material (two AI-generated reference images that disagree with
each other and with the typed correspondence tables in several places).

MAYAN TZOLKIN LAYER: two more tools (get_mayan_sign, get_mayan_tree_of_life)
look up the 260-day Tzolkin reading (Day Sign, Galactic Tone, Trecena,
Kin number) for any date, purely from the date -- no time or location
needed, unlike a chart. Deliberately NOT wired into score_wealth's boost
pipeline: unlike Gates or Typology, there's no source-grounded mapping
from a Tzolkin day sign to a specific tracked body/planet to check
resonance against, and inventing one would mean fabricating a whole
correspondence table with zero textual basis, not constructing a
reasonable interpretation of something described. See
tools/mayan_calendar.py's module docstring for exactly what's verified
(the core Tzolkin math, against three independent reference dates) vs.
constructed (the Tree of Life's past/future/masculine/feminine positions,
since the source material describes the concept but never discloses the
formula).

NUMEROLOGY LAYER: get_natal_chart takes one more optional field,
numerology_name -- GIVEN, same as enneagram_type/mbti_type. Unlike every
other layer in this project, this one is wired EXACTLY the way your own
wealth_algorithm.py does it: score_wealth's numerology boost is ADDITIVE,
folded into the raw score BEFORE normalization (raw = aspects + dignities
+ numerology), not a multiplier on the normalized 0-100 score like the
Calendar/Gate/Typology tiers. MISSING DEPENDENCY: ciphers.js (the actual
15-cipher letter-value table) was not included in this upload -- the
engine is fully ported and verified (see tools/numerology.py's module
docstring for exactly how), but produces nothing without that file
present. If numerology_name is given and ciphers.js isn't found, say so
plainly and continue without that tier -- exactly what wealth_algorithm.py
itself does, never silently substitute invented cipher values.

Run from inside the wealth_agent/ directory: `python agent_loop.py`
Requires: ANTHROPIC_API_KEY environment variable set to a real key.
"""

from __future__ import annotations

import json
import os
from datetime import date as _date
from typing import Any, Dict, Optional

import anthropic

from tools.chart import (
    get_natal_chart, chart_to_dict, NatalChart,
    PLANET_CATALOG, COMPUTED_WEIGHTS,
)
from tools.scoring import (
    score_wealth, score_result_to_dict,
    score_aspects, score_dignities, finalize_wealth_score,
)
from tools.calendar_bridge import cosmic_day_to_date, date_to_cosmic_day
from tools.gate_calendar_bridge import apply_all_cosmic_boosts
from tools.gates import (
    handle_get_gate_for_longitude,
    handle_get_chart_gates,
    handle_get_day_gate,
)
from tools.typology import (
    bodies_to_archetype_wheel,
    apply_typology_boost,
    ENNEAGRAM_CORE,
    MBTI_CONSTELLATIONS,
    MBTI_BY_CONSTELLATION,
    VALID_MBTI_CODES,
)
from tools.mayan_calendar import date_to_tzolkin, tree_of_life
from tools.numerology import (
    compute_numerology_profile,
    score_numerology_boost,
    numerology_profile_to_dict,
    ciphers_js_available,
    DEFAULT_CIPHERS_JS_PATH,
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
White Moon Selena, plus 30 fixed stars/deep-space points (incl. Galactic \
Center, Super Galactic Center, and the Solar Apex). Chiron is NOT a \
tracked body here -- it only labels Ophiuchus's traditional rulership. \
Don't claim a Chiron position exists or was computed.

Custom rulerships: Venus rules Virgo, Mercury rules Libra (in addition to \
their traditional signs). Aspects include three metallic-ratio angles \
(Golden, Silver, Bronze) alongside the standard set -- a single pair of \
bodies CAN trigger more than one aspect simultaneously if orbs overlap; \
that's expected, not a bug to paper over.

Always call get_natal_chart before score_wealth for a new person -- \
score_wealth reads the previously stored chart by label rather than \
taking birth data directly. Use recall_chart / list_recalled_charts when \
a user references someone already computed this session.

64-Gate Human Design layer: every body's sidereal longitude also maps to \
one of 64 Gates (I Ching hexagram, keyed to the chemical element sharing \
its atomic number) via get_chart_gates / get_gate_for_longitude / \
get_day_gate. This is an independent overlay on the same sidereal ring as \
the 13-sign constellations -- a body's Gate and its constellation don't \
share a boundary edge, by design, so report both without trying to \
reconcile them into one system. score_wealth's boost pipeline includes a \
day-gate tier (x1.15): unlike the month-ruler and suit-element tiers \
(both evaluated at the chart's own birth date), the day-gate tier compares \
the chart against the Sun's CURRENTLY TRANSITING Gate by default -- it's a \
"does this chart resonate with today" check, not a birth-data check. \
HOUSE FIELDS ARE CURRENTLY UNAVAILABLE: every "house" field returns None. \
The uploaded wealth_algorithm.py has no house system yet, despite one \
being described in accompanying documentation -- say so plainly if asked \
about a body's House rather than guessing or inventing one.

Enneagram/MBTI typology: enneagram_type and mbti_type on a chart are \
GIVEN facts the person states about themselves -- never infer, guess, or \
compute one from a chart. If neither is stated, don't bring the topic up \
unprompted. When at least one is stated, score_wealth automatically checks \
it for resonance (a four-tier boost, after month-ruler/suit-element/day- \
gate): does the type's ruling planet show up active in the chart, and does \
any tracked body sit in one of the type's constellations on a separate, \
independent 13-constellation wheel (Sagittarius=0 sidereal degrees -- NOT \
the same boundaries as the regular 13-sign chart, by design, the same way \
the Gate wheel doesn't share edges with it either). The source data for \
this wheel has real gaps and inconsistencies between its two reference \
images -- if asked why a specific cell looks off, say so plainly rather \
than smoothing over it.

Mayan Tzolkin: get_mayan_sign and get_mayan_tree_of_life work from a date \
alone (birth_date, today, or any other date) -- no chart needed, and \
NOT wired into score_wealth's boost pipeline (there's no source-grounded \
day-sign-to-planet correspondence to check resonance against, unlike \
Gates or Typology). The core reading (Day Sign, Tone, Trecena, Kin) is \
verified Tzolkin math -- present it plainly. The Tree of Life's four \
outer positions (past/future/masculine/feminine) are explicitly a \
constructed interpretation, not verified against any real source -- say \
so if asked, don't present them with the confidence of the center reading.

Numerology: numerology_name on a chart is GIVEN, same as enneagram_type/ \
mbti_type -- ask, don't infer. Unlike every other boost tier, numerology's \
is ADDITIVE and pre-normalization (mirrors your own wealth_algorithm.py's \
main() exactly: raw = aspects + dignities + numerology, then normalize), \
not a multiplier on the final 0-100 score. It requires ciphers.js, which \
is NOT currently available -- score_wealth and get_numerology_profile \
both return a plain, specific error/note when it's missing rather than a \
fabricated result. If a person asks for their numerology and it's \
unavailable, say exactly that (missing cipher data file) rather than \
producing a plausible-sounding profile from general numerology knowledge \
-- this project's numerology tier is specifically the 15-cipher irrational- \
constant ring from tools/numerology.py, not generic numerology.

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
            "30 fixed stars/deep-space points, ascendant, and day/night status -- and store "
            "it under a label for later recall. Always call this before "
            "score_wealth for a new person. enneagram_type/mbti_type are "
            "GIVEN facts the person states about themselves (never inferred "
            "or computed) -- ask if the person wants typology resonance "
            "included but don't guess a value they haven't stated."
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
                "enneagram_type": {
                    "type": "integer",
                    "description": "Optional. The person's self-known Enneagram core type, 1-9. Omit if not stated.",
                },
                "mbti_type": {
                    "type": "string",
                    "description": "Optional. The person's self-known 4-letter MBTI code (e.g. 'INTJ'). Omit if not stated.",
                },
                "numerology_name": {
                    "type": "string",
                    "description": (
                        "Optional. Name to run through the numerology cipher ring "
                        "(may differ from the chart label, e.g. a full legal name). "
                        "Omit to skip the numerology tier. Currently non-functional "
                        "without ciphers.js -- see system prompt."
                    ),
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
            "dignity/debility bonuses, and three automatic boosts -- Cosmic "
            "Calendar month-ruler / suit-element (from the chart's own "
            "birth date) plus a day-gate resonance boost (from as_of_date, "
            "default today)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Label used in get_natal_chart"},
                "as_of_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD. Date the day-gate transit boost is evaluated at. Defaults to today if omitted.",
                },
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
    {
        "name": "get_gate_for_longitude",
        "description": (
            "Resolve a single sidereal (Lahiri) ecliptic longitude to its "
            "64-Gate Human Design placement: Gate, Line (1-6), the gate's "
            "keyed chemical element, and I Ching hexagram. Use for a "
            "quick one-off lookup when a longitude is already known -- no "
            "chart computation involved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sidereal_longitude": {
                    "type": "number",
                    "description": "Sidereal ecliptic longitude in decimal degrees, 0-360.",
                },
            },
            "required": ["sidereal_longitude"],
        },
    },
    {
        "name": "get_chart_gates",
        "description": (
            "Compute the full 64-Gate placement (Gate, Line, element, "
            "hexagram, 13-sign sidereal constellation) for all 14 tracked "
            "bodies in a birth or transit chart. This is an independent "
            "overlay on the same sidereal ring as get_natal_chart's "
            "constellations -- the two don't share a boundary edge by "
            "design. House is currently always null (see system prompt)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "birth_date": {"type": "string", "description": "YYYY-MM-DD (UTC)"},
                "birth_time": {"type": "string", "description": "HH:MM:SS (UTC). Defaults to 12:00:00 if omitted."},
                "latitude": {"type": "number", "description": "N positive, S negative"},
                "longitude": {"type": "number", "description": "E positive, W negative"},
                "name": {"type": "string", "description": "Optional label for the native/chart."},
            },
            "required": ["birth_date", "latitude", "longitude"],
        },
    },
    {
        "name": "get_day_gate",
        "description": (
            "Get the 'Day Gate' for a civil date -- the Gate and Line the "
            "Sun sidereally occupies that day, plus the cosmic_calendar "
            "playing card for context. This is the same value score_wealth's "
            "day-gate boost tier compares a chart's own Gates against."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "YYYY-MM-DD. Defaults to today (UTC) if omitted.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_typology_info",
        "description": (
            "Look up an Enneagram type or MBTI code's planetary/"
            "constellation correspondences on the rebased (Sagittarius=0) "
            "wheel -- no chart needed. Use for a quick explanation ('what "
            "does INTJ correspond to') separate from checking resonance "
            "against an actual chart, which score_wealth does automatically "
            "once a chart has enneagram_type/mbti_type stored."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "enneagram_type": {"type": "integer", "description": "1-9"},
                "mbti_type": {"type": "string", "description": "4-letter MBTI code"},
            },
            "required": [],
        },
    },
    {
        "name": "get_mayan_sign",
        "description": (
            "Look up the 260-day Tzolkin reading for a civil date -- Day "
            "Sign, Galactic Tone, Trecena, and Kin number. Purely a "
            "function of the date, no time or location needed. Use "
            "birth_date for a person's own Mayan sign, or any other date "
            "for the day's current energy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_mayan_tree_of_life",
        "description": (
            "The 5-position Tree of Life for a date: center (that date's "
            "own Tzolkin reading) plus past/future/masculine/feminine. "
            "IMPORTANT: only 'center' is verified Tzolkin math -- the four "
            "surrounding positions are a constructed interpretation (the "
            "source material never discloses the actual formula). Say so "
            "if asked, don't present them with the same confidence as center."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_numerology_profile",
        "description": (
            "Compute a standalone numerology profile (life path number + "
            "all 15 active ciphers) for a name and birth date, without "
            "needing a full chart or running score_wealth. Requires "
            "ciphers.js to be present -- if it returns an error about a "
            "missing file, say so plainly rather than estimating or "
            "inventing cipher values."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to run through the cipher ring"},
                "birth_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["name", "birth_date"],
        },
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
        enneagram_type=chart_dict.get("enneagram_type"), mbti_type=chart_dict.get("mbti_type"),
        numerology_name=chart_dict.get("numerology_name"),
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
                enneagram_type = tool_input.get("enneagram_type")
                mbti_type = tool_input.get("mbti_type")
                numerology_name = tool_input.get("numerology_name")
                if mbti_type is not None and mbti_type.strip().upper() not in VALID_MBTI_CODES:
                    return {"error": f"'{mbti_type}' isn't a real 4-letter MBTI code "
                                      f"(valid: {sorted(VALID_MBTI_CODES)})"}

                cached = self.cache.get(bd, bt, lat, lon)
                if cached is not None:
                    chart_dict = dict(cached)
                else:
                    chart = get_natal_chart(bd, bt, lat, lon, sidereal=True)  # always sidereal
                    chart_dict = chart_to_dict(chart)
                    # Cache only the astronomical portion. enneagram_type/
                    # mbti_type/numerology_name are per-PERSON metadata,
                    # not tied to (date,time,lat,lon) -- baking them into
                    # the disk cache could leak one person's stated data
                    # onto a different chart that happens to share birth data.
                    cacheable = dict(chart_dict)
                    cacheable.pop("enneagram_type", None)
                    cacheable.pop("mbti_type", None)
                    cacheable.pop("numerology_name", None)
                    self.cache.set(bd, bt, lat, lon, cacheable)

                chart_dict["enneagram_type"] = enneagram_type
                chart_dict["mbti_type"] = mbti_type.strip().upper() if mbti_type else None
                chart_dict["numerology_name"] = numerology_name

                self.session.store(label, chart_dict)
                return chart_dict

            elif tool_name == "score_wealth":
                label = tool_input["label"]
                chart_dict = self.session.get(label)
                if chart_dict is None:
                    return {"error": f"No chart stored under label '{label}'. "
                                      f"Call get_natal_chart first."}
                nc = _rebuild_natal_chart(chart_dict)

                # Compute aspects/dignities directly (not via score_wealth()'s
                # convenience wrapper) because numerology needs those logs
                # BEFORE the raw score is finalized -- it scales each cipher's
                # ruling planet's already-computed contribution, exactly like
                # your source's main() computes asp_score/dig_bonus first,
                # then num_boost from them, then sums all three into raw.
                asp_total, asp_log = score_aspects(nc.positions, nc.weights, nc.star_positions)
                dig_total, dig_log = score_dignities(nc.positions, nc.weights, nc.body_info)

                numerology_boost = 0.0
                numerology_note = None
                numerology_log = None
                if nc.numerology_name:
                    if not ciphers_js_available():
                        numerology_note = (
                            f"Numerology requested (name='{nc.numerology_name}') but "
                            f"ciphers.js isn't available at {DEFAULT_CIPHERS_JS_PATH} -- "
                            f"skipped, not estimated. Upload the real cipher file to enable this tier."
                        )
                    else:
                        try:
                            y, m, d = (int(p) for p in nc.birth_date.split("-"))
                            profile = compute_numerology_profile(nc.numerology_name, (y, m, d))
                            numerology_boost, numerology_log = score_numerology_boost(
                                profile, asp_log, dig_log
                            )
                        except Exception as exc:
                            numerology_note = f"Numerology failed: {exc} -- skipped."
                            numerology_boost = 0.0

                wealth_result = finalize_wealth_score(
                    asp_total, dig_total, asp_log, dig_log, nc.is_day, numerology_boost
                )
                result_dict = score_result_to_dict(wealth_result, max_aspect_log=25)
                if numerology_log:
                    result_dict["numerology_log"] = numerology_log
                    result_dict["boosts_applied"].append(
                        f"numerology boost ({nc.numerology_name}, "
                        f"{numerology_boost:+.2f} added to raw score before normalization)"
                    )
                if numerology_note:
                    result_dict["numerology_note"] = numerology_note

                birth_greg_date = _date.fromisoformat(chart_dict["birth_date"])
                as_of = tool_input.get("as_of_date")
                as_of_date = _date.fromisoformat(as_of) if as_of else None
                result_dict = apply_all_cosmic_boosts(
                    result_dict, nc.positions, birth_greg_date, as_of_date=as_of_date
                )

                if nc.enneagram_type is not None or nc.mbti_type is not None:
                    bodies_involved = set()
                    for e in result_dict.get("aspect_log", []):
                        bodies_involved.update(p.strip() for p in e["pair"].split(" / "))
                    for e in result_dict.get("dignity_log", []):
                        bodies_involved.add(e["planet"])
                    body_constellations = bodies_to_archetype_wheel(nc.positions)
                    result_dict = apply_typology_boost(
                        result_dict, nc.enneagram_type, nc.mbti_type,
                        bodies_involved, body_constellations,
                    )

                return result_dict

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

            elif tool_name == "get_gate_for_longitude":
                return handle_get_gate_for_longitude(tool_input["sidereal_longitude"])

            elif tool_name == "get_chart_gates":
                return handle_get_chart_gates(
                    birth_date=tool_input["birth_date"],
                    latitude=tool_input["latitude"],
                    longitude=tool_input["longitude"],
                    birth_time=tool_input.get("birth_time", "12:00:00"),
                    name=tool_input.get("name", "Native"),
                )

            elif tool_name == "get_day_gate":
                return handle_get_day_gate(tool_input.get("date", ""))

            elif tool_name == "get_typology_info":
                ent = tool_input.get("enneagram_type")
                mbti = tool_input.get("mbti_type")
                out: Dict[str, Any] = {}
                if ent is not None:
                    if ent in ENNEAGRAM_CORE:
                        out["enneagram"] = {"type": ent, **ENNEAGRAM_CORE[ent]}
                    else:
                        out["enneagram_error"] = f"{ent} isn't a valid Enneagram type (1-9)"
                if mbti is not None:
                    code = mbti.strip().upper()
                    if code in VALID_MBTI_CODES:
                        out["mbti"] = {
                            "code": code,
                            "constellations": [
                                {"constellation": c, "archetype": a, "ruler": MBTI_BY_CONSTELLATION[c]["ruler"]}
                                for c, a in MBTI_CONSTELLATIONS[code]
                            ],
                        }
                    else:
                        out["mbti_error"] = f"'{mbti}' isn't a real 4-letter MBTI code"
                if not out:
                    out["error"] = "Provide enneagram_type and/or mbti_type"
                return out

            elif tool_name == "get_mayan_sign":
                try:
                    d = _date.fromisoformat(tool_input["date"])
                except ValueError as exc:
                    return {"error": f"Date parse error: {exc}"}
                return date_to_tzolkin(d)

            elif tool_name == "get_mayan_tree_of_life":
                try:
                    d = _date.fromisoformat(tool_input["date"])
                except ValueError as exc:
                    return {"error": f"Date parse error: {exc}"}
                return tree_of_life(d)

            elif tool_name == "get_numerology_profile":
                if not ciphers_js_available():
                    return {"error": (
                        f"ciphers.js isn't available at {DEFAULT_CIPHERS_JS_PATH}. "
                        f"The numerology engine is ready but has no cipher data to "
                        f"work with -- this isn't estimable without the real file."
                    )}
                try:
                    y, m, d = (int(p) for p in tool_input["birth_date"].split("-"))
                    profile = compute_numerology_profile(tool_input["name"], (y, m, d))
                    return numerology_profile_to_dict(profile)
                except Exception as exc:
                    return {"error": f"{type(exc).__name__}: {exc}"}

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
