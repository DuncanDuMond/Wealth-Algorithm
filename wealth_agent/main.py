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
from tools.scoring import score_wealth, score_result_to_dict
from tools.calendar_bridge import date_to_cosmic_day, apply_cosmic_boosts
from cache import ChartCache


def run_direct(birth_date: str, birth_time: str, lat: float, lon: float) -> None:
    cache = ChartCache()
    cached = cache.get(birth_date, birth_time, lat, lon)
    if cached is not None:
        chart_dict = cached
        print("(loaded from cache)", file=sys.stderr)
    else:
        chart = get_natal_chart(birth_date, birth_time, lat, lon, sidereal=True)
        chart_dict = chart_to_dict(chart)
        cache.set(birth_date, birth_time, lat, lon, chart_dict)

    if chart_dict["errors"]:
        print("Chart computed with warnings:", file=sys.stderr)
        for err in chart_dict["errors"]:
            print(f"  - {err}", file=sys.stderr)

    from agent_loop import _rebuild_natal_chart  # reuse the same rebuild path
    nc = _rebuild_natal_chart(chart_dict)
    result_dict = score_result_to_dict(score_wealth(nc))
    cosmic_info = date_to_cosmic_day(birth_date)
    boosted = apply_cosmic_boosts(result_dict, cosmic_info)

    print(json.dumps({"chart": chart_dict, "score": boosted}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Wealth algorithm agent CLI")
    parser.add_argument("--direct", nargs=4,
                         metavar=("BIRTH_DATE", "BIRTH_TIME", "LATITUDE", "LONGITUDE"),
                         help="Run chart+score directly without the Anthropic agent, "
                              "e.g. --direct 1994-03-21 14:30:00 40.7128 -74.0060")
    args = parser.parse_args()

    if args.direct:
        birth_date, birth_time, lat, lon = args.direct
        run_direct(birth_date, birth_time, float(lat), float(lon))
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