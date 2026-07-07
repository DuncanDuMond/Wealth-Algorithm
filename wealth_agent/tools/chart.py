"""
chart.py — Natal chart position calculations.

FAITHFUL PORT of the position-calculation logic from your uploaded
wealth_algorithm.py (PLANET_CATALOG, COMPUTED_WEIGHTS, STAR_CATALOG,
sign_tropical, sign_sidereal_13, calc_planets, calc_ascendant, calc_lots,
calc_selena, calc_stars, all_body_positions, setup_ephemeris) — same
constants, same formulas, same body list. Not a reinterpretation.

FRAMEWORK NOTE: your original script defaults to TROPICAL and takes
--sidereal to switch modes. Per your standing instruction for this
project, the agent layer (agent_loop.py) always calls get_natal_chart
with sidereal=True and never exposes a tropical option to the model.
The sidereal=False code path is kept here only because it exists in your
source script -- direct callers of chart.py can still use it if needed.

Tracked bodies (14 total, matching your script exactly):
  10 classical/modern planets + True Black Moon Lilith (11 "planets")
  + Lot of Fortune, Lot of Spirit, White Moon Selena (3 computed points)
Chiron is NOT a tracked/scored body in your script -- it appears only as
a comment labeling Ophiuchus's traditional ruler. See calendar_bridge.py
for how that's handled in the month-ruler boost.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import swisseph as swe

# ---------------------------------------------------------------------------
# Ephemeris setup -- ported from setup_ephemeris(). sefstars.txt is
# auto-downloaded on first use, exactly as your script does, from the same
# source URL. Path handling uses pathlib, resolved relative to this file
# (not cwd) so it works the same whether invoked from PowerShell, VSCode,
# or elsewhere, per your Windows/OneDrive portability preference.
# ---------------------------------------------------------------------------
_SEFSTARS_URL = "https://github.com/aloistr/swisseph/raw/master/ephe/sefstars.txt"
EPHE_DIR = Path(__file__).resolve().parent.parent / "ephe"

_ephemeris_ready = False


def setup_ephemeris(ephe_dir: Optional[str] = None) -> None:
    """Locate/create the ephemeris directory, register it with pyswisseph,
    and download sefstars.txt if it isn't already present. Idempotent --
    safe to call multiple times (e.g. once per chart) without re-downloading."""
    global _ephemeris_ready
    ephe_path = Path(ephe_dir).expanduser().resolve() if ephe_dir else EPHE_DIR
    ephe_path.mkdir(parents=True, exist_ok=True)
    stars_file = ephe_path / "sefstars.txt"

    if not stars_file.exists():
        try:
            urllib.request.urlretrieve(_SEFSTARS_URL, str(stars_file))
        except Exception as exc:
            # Non-fatal: chart/planet calc still works, only fixed stars
            # are affected, and calc_stars() reports the miss per-star.
            print(f"  [!] sefstars.txt download failed: {exc}")

    swe.set_ephe_path(str(ephe_path))
    _ephemeris_ready = True


def _ensure_ephemeris() -> None:
    if not _ephemeris_ready:
        setup_ephemeris()


# ---------------------------------------------------------------------------
# PLANETARY CATALOG -- verbatim from wealth_algorithm.py.
# weight = wealth relevance (1-10), used later by the scoring engine.
# ---------------------------------------------------------------------------
PLANET_CATALOG: Dict[str, dict] = {
    "Sun":      {"id": swe.SUN,       "weight":  6},
    "Moon":     {"id": swe.MOON,      "weight":  5},
    "Mercury":  {"id": swe.MERCURY,   "weight":  5},   # rules Libra (custom)
    "Venus":    {"id": swe.VENUS,     "weight":  9},   # rules Virgo (custom)
    "Mars":     {"id": swe.MARS,      "weight":  4},
    "Jupiter":  {"id": swe.JUPITER,   "weight": 10},
    "Saturn":   {"id": swe.SATURN,    "weight":  5},
    "Uranus":   {"id": swe.URANUS,    "weight":  5},
    "Neptune":  {"id": swe.NEPTUNE,   "weight":  4},
    "Pluto":    {"id": swe.PLUTO,     "weight":  6},
    "True BML": {"id": swe.OSCU_APOG, "weight":  4},   # True Black Moon Lilith
}

COMPUTED_WEIGHTS: Dict[str, int] = {
    "Lot of Fortune":    10,
    "Lot of Spirit":      8,
    "White Moon Selena":  6,
}

# ---------------------------------------------------------------------------
# FIXED STAR CATALOG -- verbatim 18-star list + fallback names.
# ---------------------------------------------------------------------------
STAR_CATALOG: Dict[str, int] = {
    "Taygeta":        4, "Arcturus":       7, "Sirius":         9,
    "Andromeda":      4, "Betelgeuse":     6, "Rigel":          7,
    "Aldebaran":      8, "Fomalhaut":      8, "Antares":        5,
    "Regulus":        9, "Scheat":         3, "Sabik":          4,
    "Rasalhague":     4, "Kaus Australis": 6, "Vega":           7,
    "Altair":         6, "Sadalsuud":      6, "Zuben Elgenubi": 5,
}

STAR_FALLBACKS: Dict[str, str] = {
    "Andromeda":      "Alpheratz",
    "Kaus Australis": "Kaus Austr",
    "Zuben Elgenubi": "Zuben Elge",
    "Taygeta":        "19Tau",
}

# ---------------------------------------------------------------------------
# ZODIAC SIGN SYSTEMS -- verbatim.
# ---------------------------------------------------------------------------
SIGNS_12: List[str] = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# IAU ecliptic constellation boundaries expressed as TROPICAL longitudes.
# Subtract the Lahiri ayanamsa (live, per-date) to obtain sidereal entry
# points -- see sign_sidereal_13(). This is your exact validated table.
_13SIGN_TROP: List[Tuple[str, float]] = [
    ("Aries",          27.86), ("Taurus",         53.46),
    ("Gemini",         90.33), ("Cancer",        119.10),
    ("Leo",           134.83), ("Virgo",         173.73),
    ("Libra",         217.81), ("Scorpio",       241.81),
    ("Ophiuchus",     247.07),   # 13th constellation; ruler = Chiron (label only)
    ("Sagittarius",   266.03), ("Capricorn",     299.70),
    ("Aquarius",      327.26), ("Pisces",        351.51),
]


def sign_tropical(lon: float) -> Tuple[str, float]:
    """12-sign tropical placement -> (sign_name, degrees_within_sign)."""
    lon = lon % 360.0
    return SIGNS_12[int(lon // 30)], lon % 30.0


def sign_sidereal_13(sid_lon: float, ayanamsa: float) -> Tuple[str, float]:
    """13-sign sidereal placement (Ophiuchus included), live ayanamsa-shifted.
    Algorithm: largest boundary entry <= sid_lon wins; Pisces is the
    default since it wraps past 0deg. Ported verbatim."""
    entries = [(n, (t - ayanamsa) % 360.0) for n, t in _13SIGN_TROP]
    sid_lon = sid_lon % 360.0
    result_name, result_start = entries[-1]  # Pisces wraps 0deg
    for name, start in entries:
        if sid_lon >= start:
            result_name, result_start = name, start
    return result_name, (sid_lon - result_start) % 360.0


def get_julian_day(year: int, month: int, day: int, hour: float) -> float:
    return swe.julday(year, month, day, hour)


# ---------------------------------------------------------------------------
# POSITION CALCULATIONS -- verbatim logic, with light per-body error capture
# added for the agent context (your original lets a single calc_ut failure
# crash the whole run; here it's recorded in chart.errors instead so the
# agent can explain it rather than the process dying mid-chart).
# ---------------------------------------------------------------------------
def calc_planets(jd: float, sidereal: bool = False) -> Tuple[Dict[str, float], Dict[str, bool], List[str]]:
    """Ecliptic longitudes + retrograde flags for all catalog planets.
    Returns (longitudes, retrograde_flags, errors)."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    if sidereal:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        flags |= swe.FLG_SIDEREAL

    lons: Dict[str, float] = {}
    retro: Dict[str, bool] = {}
    errors: List[str] = []
    for name, data in PLANET_CATALOG.items():
        try:
            xx, _ = swe.calc_ut(jd, data["id"], flags)
            lons[name] = xx[0] % 360.0
            retro[name] = xx[3] < 0.0  # negative speed -> retrograde
        except swe.Error as e:
            errors.append(f"{name}: {e}")
    return lons, retro, errors


def calc_ascendant(jd: float, lat: float, lon: float, sidereal: bool = False) -> float:
    """Placidus Ascendant. In sidereal mode the tropical value is corrected
    by subtracting the live Lahiri ayanamsa for this jd."""
    _, ascmc = swe.houses(jd, lat, lon, b"P")
    asc = ascmc[0]
    if sidereal:
        asc = (asc - swe.get_ayanamsa_ut(jd)) % 360.0
    return asc


def is_day_chart(sun_lon: float, asc: float) -> bool:
    """True when the Sun is above the horizon (houses 7-12)."""
    return ((sun_lon - asc) % 360.0) > 180.0


def calc_lots(asc: float, sun: float, moon: float, day: bool) -> Dict[str, float]:
    """Hellenistic Lots with Ptolemaic day/night reversal."""
    if day:
        return {"Lot of Fortune": (asc + moon - sun) % 360.0,
                "Lot of Spirit":  (asc + sun - moon) % 360.0}
    return {"Lot of Fortune": (asc + sun - moon) % 360.0,
            "Lot of Spirit":  (asc + moon - sun) % 360.0}


def calc_selena(bml_lon: float) -> float:
    """True White Moon Selena = True Black Moon Lilith + 180deg."""
    return (bml_lon + 180.0) % 360.0


def _fetch_star(name: str, jd: float, flags: int) -> Optional[float]:
    """Resolve a fixed star longitude, trying the primary catalog name
    then its fallback (if any)."""
    candidates = [name] + ([STAR_FALLBACKS[name]] if name in STAR_FALLBACKS else [])
    for candidate in candidates:
        try:
            xx, _sname, _ret = swe.fixstar_ut(candidate, jd, flags)
            return xx[0] % 360.0
        except Exception:
            continue
    return None


def calc_stars(jd: float) -> Tuple[Dict[str, float], List[str]]:
    """Ecliptic longitudes for all 18 catalog fixed stars.
    Returns (positions, names_not_resolved)."""
    _ensure_ephemeris()
    flags = swe.FLG_SWIEPH
    out: Dict[str, float] = {}
    missing: List[str] = []
    for name in STAR_CATALOG:
        lon = _fetch_star(name, jd, flags)
        if lon is not None:
            out[name] = lon
        else:
            missing.append(name)
    return out, missing


BodyInfo = Dict


def all_body_positions(
    jd: float, lat: float, lon: float, sidereal: bool = False
) -> Tuple[Dict[str, float], Dict[str, int], Dict[str, BodyInfo], List[str]]:
    """Compute every tracked body (11 planets + 3 computed points).
    Returns (positions, weights, body_info, errors)."""
    lons, retro, errors = calc_planets(jd, sidereal)
    ayana = swe.get_ayanamsa_ut(jd) if sidereal else 0.0

    asc = calc_ascendant(jd, lat, lon, sidereal)
    day = is_day_chart(lons["Sun"], asc) if "Sun" in lons else True

    if "Sun" in lons and "Moon" in lons:
        lons.update(calc_lots(asc, lons["Sun"], lons["Moon"], day))
    if "True BML" in lons:
        lons["White Moon Selena"] = calc_selena(lons["True BML"])

    weights = {n: d["weight"] for n, d in PLANET_CATALOG.items()}
    weights.update(COMPUTED_WEIGHTS)

    info: Dict[str, BodyInfo] = {}
    for name, body_lon in lons.items():
        if sidereal:
            sign, deg = sign_sidereal_13(body_lon, ayana)
        else:
            sign, deg = sign_tropical(body_lon)
        info[name] = {
            "lon": round(body_lon, 6),
            "sign": sign,
            "deg_in_sign": round(deg, 4),
            "retro": retro.get(name, False),
        }

    return lons, weights, info, errors


@dataclass
class NatalChart:
    """Agent-facing wrapper around all_body_positions() + calc_stars().
    birth_date/time/lat/lon are kept for cache keys and calendar-bridge
    date lookups -- they aren't part of your original script's return
    values, which only needed the Julian day."""
    birth_date: str
    birth_time: str
    latitude: float
    longitude: float
    julian_day: float
    sidereal: bool
    ascendant: float = 0.0
    is_day: bool = True
    positions: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, int] = field(default_factory=dict)
    body_info: Dict[str, dict] = field(default_factory=dict)
    star_positions: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


def get_natal_chart(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    sidereal: bool = True,
) -> NatalChart:
    """
    Compute a natal chart. sidereal=True (Lahiri, 13-sign incl. Ophiuchus)
    per your standing instruction -- the agent layer never passes False.

    Args:
        birth_date: "YYYY-MM-DD"
        birth_time: "HH:MM:SS" (24hr, UT) -- matches your script's format
        latitude / longitude: birth location, decimal degrees
    """
    _ensure_ephemeris()
    y, m, d = (int(p) for p in birth_date.split("-"))
    parts = birth_time.split(":")
    hh, mm = int(parts[0]), int(parts[1])
    ss = int(parts[2]) if len(parts) > 2 else 0
    hour_decimal = hh + mm / 60.0 + ss / 3600.0
    jd = get_julian_day(y, m, d, hour_decimal)

    positions, weights, body_info, errors = all_body_positions(jd, latitude, longitude, sidereal)
    star_positions, missing_stars = calc_stars(jd)
    for star in missing_stars:
        errors.append(f"Fixed star '{star}' not found in sefstars.txt -- skipped.")

    asc = calc_ascendant(jd, latitude, longitude, sidereal)
    day = is_day_chart(positions.get("Sun", 0.0), asc)

    return NatalChart(
        birth_date=birth_date, birth_time=birth_time,
        latitude=latitude, longitude=longitude,
        julian_day=jd, sidereal=sidereal,
        ascendant=asc, is_day=day,
        positions=positions, weights=weights, body_info=body_info,
        star_positions=star_positions, errors=errors,
    )


def chart_to_dict(chart: NatalChart) -> dict:
    """Serialize a NatalChart to a plain dict -- the tool result payload
    returned to the agent loop."""
    return {
        "birth_date": chart.birth_date,
        "birth_time": chart.birth_time,
        "latitude": chart.latitude,
        "longitude": chart.longitude,
        "sidereal": chart.sidereal,
        "zodiac": "13-sign sidereal (Lahiri, Ophiuchus incl.)" if chart.sidereal else "12-sign tropical",
        "ascendant": round(chart.ascendant, 4),
        "is_day_chart": chart.is_day,
        "bodies": chart.body_info,
        "fixed_stars": {s: round(v, 6) for s, v in chart.star_positions.items()},
        "errors": chart.errors,
    }