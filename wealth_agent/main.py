"""
main.py — CLI entry point.

Two modes:
  python main.py --direct BIRTH_DATE BIRTH_TIME LAT LON
      Runs the chart + score pipeline directly, no Anthropic API call,
      no API key needed. Useful for validating the astrology/scoring
      logic in isolation before wiring it into the agent.

  python main.py
      Starts the interactive tool-calling agent (agent_loop.WealthAgent).
      Requires ANTHROPIC_API_KEY to be set.
"""

from __future__ import annotations

import argparse
import json
import sys

from tools.chart import get_natal_chart, chart_to_dict
from tools.scoring import (
    score_wealth, score_result_to_dict,
    score_aspects, score_dignities, finalize_wealth_score,
)
from tools.gate_calendar_bridge import apply_all_cosmic_boosts
from tools.human_design_gates import bodies_to_gates
from tools.typology import bodies_to_archetype_wheel, apply_typology_boost, VALID_MBTI_CODES
from tools.mayan_calendar import date_to_tzolkin, tree_of_life
from tools.numerology import (
    compute_numerology_profile, score_numerology_boost,
    ciphers_js_available, DEFAULT_CIPHERS_JS_PATH,
)
from cache import ChartCache


def run_direct(
    birth_date: str, birth_time: str, lat: float, lon: float,
    enneagram_type: int | None = None, mbti_type: str | None = None,
    numerology_name: str | None = None,
) -> None:
    cache = ChartCache()
    cached = cache.get(birth_date, birth_time, lat, lon)
    if cached is not None:
        chart_dict = dict(cached)
        print("(loaded from cache)", file=sys.stderr)
    else:
        chart = get_natal_chart(birth_date, birth_time, lat, lon, sidereal=True)
        chart_dict = chart_to_dict(chart)
        cacheable = dict(chart_dict)
        cacheable.pop("enneagram_type", None)
        cacheable.pop("mbti_type", None)
        cacheable.pop("numerology_name", None)
        cache.set(birth_date, birth_time, lat, lon, cacheable)

    chart_dict["enneagram_type"] = enneagram_type
    chart_dict["mbti_type"] = mbti_type.strip().upper() if mbti_type else None
    chart_dict["numerology_name"] = numerology_name

    if chart_dict["errors"]:
        print("Chart computed with warnings:", file=sys.stderr)
        for err in chart_dict["errors"]:
            print(f"  - {err}", file=sys.stderr)

    from agent_loop import _rebuild_natal_chart  # reuse the same rebuild path
    from datetime import date as _date
    nc = _rebuild_natal_chart(chart_dict)

    # Additive numerology boost, computed from aspects/dignities BEFORE
    # normalization -- see agent_loop.py's module docstring for why this
    # can't just call score_wealth() directly when numerology is involved.
    asp_total, asp_log = score_aspects(nc.positions, nc.weights, nc.star_positions)
    dig_total, dig_log = score_dignities(nc.positions, nc.weights, nc.body_info)
    numerology_boost = 0.0
    numerology_log = None
    if numerology_name:
        if not ciphers_js_available():
            print(f"  [!] Numerology: ciphers.js not found at {DEFAULT_CIPHERS_JS_PATH} -- skipped.",
                  file=sys.stderr)
        else:
            y, m, d = (int(p) for p in birth_date.split("-"))
            profile = compute_numerology_profile(numerology_name, (y, m, d))
            numerology_boost, numerology_log = score_numerology_boost(profile, asp_log, dig_log)
    wealth_result = finalize_wealth_score(asp_total, dig_total, asp_log, dig_log, nc.is_day, numerology_boost)
    result_dict = score_result_to_dict(wealth_result)
    if numerology_log:
        result_dict["numerology_log"] = numerology_log
        result_dict["boosts_applied"].append(
            f"numerology boost ({numerology_name}, "
            f"{numerology_boost:+.2f} added to raw score before normalization)"
        )

    boosted = apply_all_cosmic_boosts(result_dict, nc.positions, _date.fromisoformat(birth_date))

    if nc.enneagram_type is not None or nc.mbti_type is not None:
        bodies_involved = set()
        for e in boosted.get("aspect_log", []):
            bodies_involved.update(p.strip() for p in e["pair"].split(" / "))
        for e in boosted.get("dignity_log", []):
            bodies_involved.add(e["planet"])
        body_constellations = bodies_to_archetype_wheel(nc.positions)
        boosted = apply_typology_boost(
            boosted, nc.enneagram_type, nc.mbti_type, bodies_involved, body_constellations
        )

    gates = bodies_to_gates(nc.positions)

    # Mayan Tzolkin is purely a function of birth_date -- no extra input
    # needed, unlike enneagram/mbti which must be given. NOT wired into
    # the score -- see agent_loop.py's module docstring for why.
    mayan = {
        "sign": date_to_tzolkin(_date.fromisoformat(birth_date)),
        "tree_of_life": tree_of_life(_date.fromisoformat(birth_date)),
    }

    print(json.dumps({"chart": chart_dict, "score": boosted, "gates": gates, "mayan": mayan}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Wealth algorithm agent CLI")
    parser.add_argument("--direct", nargs=4,
                         metavar=("BIRTH_DATE", "BIRTH_TIME", "LATITUDE", "LONGITUDE"),
                         help="Run chart+score directly without the Anthropic agent, "
                              "e.g. --direct 1994-03-21 14:30:00 40.7128 -74.0060")
    parser.add_argument("--enneagram", type=int, metavar="TYPE",
                         help="Optional Enneagram core type (1-9), only used with --direct")
    parser.add_argument("--mbti", type=str, metavar="CODE",
                         help="Optional 4-letter MBTI code, only used with --direct")
    parser.add_argument("--numerology-name", type=str, metavar="NAME",
                         help="Optional name to run through the numerology cipher ring, "
                              "only used with --direct. Requires ciphers.js to be present "
                              "(see tools/numerology.py) -- skipped with a warning otherwise.")
    args = parser.parse_args()

    if args.direct:
        if args.mbti and args.mbti.strip().upper() not in VALID_MBTI_CODES:
            raise SystemExit(f"'{args.mbti}' isn't a real 4-letter MBTI code")
        birth_date, birth_time, lat, lon = args.direct
        run_direct(birth_date, birth_time, float(lat), float(lon),
                   enneagram_type=args.enneagram, mbti_type=args.mbti,
                   numerology_name=args.numerology_name)
    else:
        from agent_loop import WealthAgent
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit(
                "Set ANTHROPIC_API_KEY before running the agent, or use "
                "--direct to test scoring without the API."
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
            print(f"\nagent> {agent.send(user_input)}\n")


if __name__ == "__main__":
    main()
