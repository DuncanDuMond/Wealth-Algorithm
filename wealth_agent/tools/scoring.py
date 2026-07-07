"""
scoring.py — Aspect detection, dignity system, and final wealth score.

FAITHFUL PORT from your uploaded wealth_algorithm.py: ASPECTS (14 exact
angle/orb/score triples), the dignity tables (RULERSHIPS/EXALTATIONS/
DETRIMENTS/FALLS/DIGNITY_SCORE), detect_aspects, orb_strength,
score_aspects (Planet-Planet + Planet-Star, STAR_FACTOR=0.70),
score_dignities, normalize(lo=-600, hi=1200), rating_label. Every
constant and formula below matches your source exactly -- cross-checked
against the uploaded file line by line, not reconstructed from memory.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .chart import NatalChart, STAR_CATALOG, SIGNS_12

# ---------------------------------------------------------------------------
# METALLIC RATIO CONSTANTS -- verbatim.
# ---------------------------------------------------------------------------
PHI = (1 + math.sqrt(5)) / 2       # Golden  phi = 1.6180339887...
DELTA = 1 + math.sqrt(2)            # Silver  delta = 2.4142135624...
BETA = (3 + math.sqrt(13)) / 2      # Bronze  beta = 3.3027756377...

GOLDEN_ANGLE = 360.0 / PHI ** 2     # 137.5077640deg
SILVER_ANGLE = 360.0 / DELTA ** 2   # 61.7317deg
BRONZE_ANGLE = 360.0 / BETA ** 2    # 33.0025deg

# ---------------------------------------------------------------------------
# ASPECT TABLE -- verbatim. angle=exact angle, orb=max orb, score=base weight.
# ---------------------------------------------------------------------------
ASPECTS: Dict[str, dict] = {
    "Conjunction":    {"angle":   0.0,        "orb": 7.0,    "score": 10.0},
    "Opposition":     {"angle": 180.0,        "orb": 6.0,    "score": -6.0},
    "Trine":          {"angle": 120.0,        "orb": 6.0,    "score":  9.0},  # Supergolden
    "Square":         {"angle":  90.0,        "orb": 5.0,    "score": -5.0},
    "Sextile":        {"angle":  60.0,        "orb": 2.5,    "score":  7.0},
    "Semisquare":     {"angle":  45.0,        "orb": 1.5,    "score": -3.0},
    "Sesquiquadrate": {"angle": 135.0,        "orb": 1.5,    "score": -3.0},
    "Semisextile":    {"angle":  30.0,        "orb": 1.0,    "score":  3.0},
    "Quincunx":       {"angle": 150.0,        "orb": 1.5,    "score": -2.0},
    "Quintile":       {"angle":  72.0,        "orb": 2.0,    "score":  5.0},
    "BiQuintile":     {"angle": 144.0,        "orb": 2.0,    "score":  5.0},
    "Golden Angle":   {"angle": GOLDEN_ANGLE, "orb": 3 + 8 / 60, "score": 8.0},
    "Silver Angle":   {"angle": SILVER_ANGLE, "orb": 3 + 8 / 60, "score": 6.0},
    "Bronze Angle":   {"angle": BRONZE_ANGLE, "orb": 1 + 8 / 60, "score": 5.0},
}

# ---------------------------------------------------------------------------
# DIGNITY SYSTEM -- verbatim. Custom rulerships: Venus -> Virgo, Mercury -> Libra.
# Keyed on the 12-sign tropical names regardless of chart sign-mode -- a
# planet transiting Ophiuchus (sidereal 13-sign only) gets no dignity
# bonus/penalty in your script, since Ophiuchus isn't a key in any of
# these four tables. Preserved as-is, not "fixed".
# ---------------------------------------------------------------------------
_OPP: Dict[str, str] = {s: SIGNS_12[(i + 6) % 12] for i, s in enumerate(SIGNS_12)}

RULERSHIPS: Dict[str, List[str]] = {
    "Sun":      ["Leo"],
    "Moon":     ["Cancer"],
    "Mercury":  ["Gemini", "Libra"],          # Libra: custom
    "Venus":    ["Taurus", "Virgo"],           # Virgo: custom
    "Mars":     ["Aries", "Scorpio"],
    "Jupiter":  ["Sagittarius", "Pisces"],
    "Saturn":   ["Capricorn", "Aquarius"],
    "Uranus":   ["Aquarius"],
    "Neptune":  ["Pisces"],
    "Pluto":    ["Scorpio"],
}

EXALTATIONS: Dict[str, str] = {
    "Sun":     "Aries",     "Moon":    "Taurus",     "Mercury": "Virgo",
    "Venus":   "Pisces",    "Mars":    "Capricorn",  "Jupiter": "Cancer",
    "Saturn":  "Libra",     "Uranus":  "Scorpio",    "Neptune": "Leo",
    "Pluto":   "Aries",
}

DETRIMENTS: Dict[str, List[str]] = {
    p: [_OPP[s] for s in signs if s in _OPP]
    for p, signs in RULERSHIPS.items()
}

FALLS: Dict[str, str] = {
    p: _OPP[s] for p, s in EXALTATIONS.items() if s in _OPP
}

DIGNITY_SCORE: Dict[str, float] = {
    "rulership":  3.0,
    "exaltation": 1.5,
    "fall":      -1.0,
    "detriment": -2.0,
}

DIG_SYMBOL: Dict[str, str] = {
    "rulership": "*", "exaltation": "^", "fall": "v", "detriment": "x", "": " ",
}  # ASCII-safe versions of your original star/triangle/cross glyphs


def planet_dignity(planet: str, sign: str) -> str:
    """'rulership' | 'exaltation' | 'fall' | 'detriment' | '' -- exact
    precedence order from your source (rulership checked before exaltation)."""
    if sign in RULERSHIPS.get(planet, []):
        return "rulership"
    if sign in DETRIMENTS.get(planet, []):
        return "detriment"
    if sign == EXALTATIONS.get(planet):
        return "exaltation"
    if sign == FALLS.get(planet):
        return "fall"
    return ""


def _dms(deg: float) -> str:
    """Decimal degrees -> D°MM'SS\" string, for orb display in logs."""
    d = int(deg)
    rem = (deg - d) * 60
    m = int(rem)
    s = round((rem - m) * 60)
    if s == 60:
        m += 1
        s = 0
    if m == 60:
        d += 1
        m = 0
    return f"{d}\u00b0{m:02d}'{s:02d}\""


def _log_entry(pair: str, kind: str, asp: str, orb: float, strength: float, contrib: float) -> dict:
    return {
        "pair": pair, "type": kind, "aspect": asp,
        "orb": round(orb, 4), "orb_dms": _dms(orb),
        "strength": round(strength, 3), "contrib": round(contrib, 3),
    }


# ---------------------------------------------------------------------------
# ASPECT ENGINE -- verbatim.
# ---------------------------------------------------------------------------
AspectHit = Tuple[str, float, float]  # (aspect_name, actual_orb, base_score)


def short_arc(lon1: float, lon2: float) -> float:
    """Minimum arc between two ecliptic longitudes (always 0-180deg)."""
    diff = abs(lon1 - lon2) % 360.0
    return min(diff, 360.0 - diff)


def detect_aspects(lon1: float, lon2: float) -> List[AspectHit]:
    """All aspects triggered between two positions (a pair CAN trigger
    more than one aspect if orbs overlap -- not artificially deduped)."""
    sep = short_arc(lon1, lon2)
    hits: List[AspectHit] = []
    for name, asp in ASPECTS.items():
        delta = abs(sep - asp["angle"])
        if delta <= asp["orb"]:
            hits.append((name, delta, asp["score"]))
    return hits


def orb_strength(actual: float, maximum: float) -> float:
    """Linear orb-strength: 1.0 at exact aspect, 0.0 at the orb boundary."""
    return 1.0 - (actual / maximum)


# ---------------------------------------------------------------------------
# SCORING ENGINE -- verbatim.
#   Planet-Planet : base_score x avg_weight x orb_strength
#   Planet-Star   : base_score x avg_weight x orb_strength x STAR_FACTOR
# ---------------------------------------------------------------------------
STAR_FACTOR = 0.70  # fixed stars contribute slightly less than moving planets


def score_aspects(
    planet_pos: Dict[str, float],
    planet_wts: Dict[str, int],
    star_pos: Dict[str, float],
) -> Tuple[float, List[dict]]:
    """Score all planet-planet and planet-star aspect pairs."""
    total = 0.0
    log: List[dict] = []
    bodies = list(planet_pos.keys())

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            w_avg = (planet_wts[b1] + planet_wts[b2]) / 2.0
            for asp, orb_used, base in detect_aspects(planet_pos[b1], planet_pos[b2]):
                sf = orb_strength(orb_used, ASPECTS[asp]["orb"])
                c = base * w_avg * sf
                total += c
                log.append(_log_entry(f"{b1} / {b2}", "P-P", asp, orb_used, sf, c))

    for planet, plon in planet_pos.items():
        pw = planet_wts[planet]
        for star, slon in star_pos.items():
            sw = STAR_CATALOG.get(star, 5)
            w_avg = (pw + sw) / 2.0
            for asp, orb_used, base in detect_aspects(plon, slon):
                sf = orb_strength(orb_used, ASPECTS[asp]["orb"])
                c = base * w_avg * sf * STAR_FACTOR
                total += c
                log.append(_log_entry(f"{planet} / {star}", "P-S", asp, orb_used, sf, c))

    log.sort(key=lambda x: abs(x["contrib"]), reverse=True)
    return total, log


def score_dignities(
    planet_pos: Dict[str, float],
    planet_wts: Dict[str, int],
    body_info: Dict[str, dict],
) -> Tuple[float, List[dict]]:
    """Per-planet dignity/debility bonus: DIGNITY_SCORE[status] x planet_weight.
    Only planets with defined rulerships are evaluated (True BML and the
    3 computed points are excluded, matching your source)."""
    total = 0.0
    log: List[dict] = []
    for planet in RULERSHIPS:
        if planet not in planet_pos or planet not in body_info:
            continue
        sign = body_info[planet]["sign"]
        dignity = planet_dignity(planet, sign)
        if not dignity:
            continue
        bonus = DIGNITY_SCORE[dignity] * planet_wts.get(planet, 1)
        total += bonus
        log.append({
            "planet": planet, "sign": sign,
            "dignity": dignity, "bonus": round(bonus, 2),
        })
    return total, log


def normalize(raw: float, lo: float = -600.0, hi: float = 1200.0) -> float:
    """Map raw score -> 0-100."""
    return max(0.0, min(100.0, (raw - lo) / (hi - lo) * 100.0))


def rating_label(s: float) -> str:
    if s >= 80:
        return "Exceptional"
    if s >= 65:
        return "Strong"
    if s >= 50:
        return "Moderate"
    if s >= 35:
        return "Developing"
    return "Challenging"


# ---------------------------------------------------------------------------
# Agent-facing wrapper
# ---------------------------------------------------------------------------
@dataclass
class WealthScoreResult:
    raw_score: float
    normalized_score: float
    rating: str
    aspect_log: List[dict] = field(default_factory=list)
    dignity_log: List[dict] = field(default_factory=list)
    is_day_chart: bool = True
    boosts_applied: List[str] = field(default_factory=list)


def score_wealth(chart: NatalChart) -> WealthScoreResult:
    """Compute the full wealth score for a NatalChart: aspects + dignities,
    normalized to 0-100 with a rating label. This is score_aspects() +
    score_dignities() + normalize() + rating_label() from your source,
    wired directly to the NatalChart produced by chart.get_natal_chart()."""
    asp_total, asp_log = score_aspects(chart.positions, chart.weights, chart.star_positions)
    dig_total, dig_log = score_dignities(chart.positions, chart.weights, chart.body_info)
    raw = asp_total + dig_total
    norm = normalize(raw)
    return WealthScoreResult(
        raw_score=round(raw, 3),
        normalized_score=round(norm, 2),
        rating=rating_label(norm),
        aspect_log=asp_log,
        dignity_log=dig_log,
        is_day_chart=chart.is_day,
    )


def score_result_to_dict(result: WealthScoreResult) -> dict:
    return {
        "raw_score": result.raw_score,
        "normalized_score": result.normalized_score,
        "rating": result.rating,
        "is_day_chart": result.is_day_chart,
        "aspect_log": result.aspect_log,
        "dignity_log": result.dignity_log,
        "boosts_applied": result.boosts_applied,
    }