# Wealth Calendar Algorithm

A two-part Python system combining a symbolic 13-month playing card calendar with an astrological wealth scoring engine. The scripts can be used independently or as the fully integrated `wealth_calendar_algorithm.py`.

---

## Table of Contents

1. [Files in This Package](#1-files-in-this-package)
2. [Requirements & Installation](#2-requirements--installation)
3. [Quick Start](#3-quick-start)
4. [cosmic\_calendar.py](#4-cosmic_calendarpy)
5. [wealth\_algorithm.py](#5-wealth_algorithmpy)
6. [wealth\_calendar\_algorithm.py — Integrated](#6-wealth_calendar_algorithmpy--integrated)
7. [Integration Bridge](#7-integration-bridge)
8. [Output Formats & JSON Schema](#8-output-formats--json-schema)
9. [Customisation & Tuning](#9-customisation--tuning)
10. [Module Structure](#10-module-structure)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Files in This Package

| File | Purpose | Requires pyswisseph |
|---|---|---|
| `cosmic_calendar.py` | 13-month Cosmic Playing Card Calendar — display and lookup | No |
| `wealth_algorithm.py` | Astrological wealth scoring — aspects, dignities, fixed stars | Yes |
| `wealth_calendar_algorithm.py` | Single-file integration of both, with bridge layer | Calendar: No · Wealth: Yes |

---

## 2. Requirements & Installation

**Python:** 3.8 or later

`cosmic_calendar.py` uses only the Python standard library. No packages required.

`wealth_algorithm.py` and the wealth mode of the integrated file require:

```bash
pip install pyswisseph
```

The Swiss Ephemeris star data file `sefstars.txt` is **downloaded automatically** on the first wealth-scoring run and saved to `ephe/sefstars.txt` next to the script. No manual setup is needed.

> The integrated file's calendar mode runs without `pyswisseph` installed. Only wealth scoring requires it.

---

## 3. Quick Start

```bash
# Today's cosmic date and card
python cosmic_calendar.py

# Look up a specific date
python cosmic_calendar.py lookup 1990-06-15

# Wealth score (interactive prompts)
python wealth_algorithm.py

# Integrated — calendar today
python wealth_calendar_algorithm.py calendar today

# Integrated — full wealth score
python wealth_calendar_algorithm.py wealth \
  --name "Alice" --date 1990-06-15 --time 14:30:00 \
  --lat 40.7128 --lon -74.0060 --sidereal --output alice.json
```

---

## 4. cosmic\_calendar.py

### Overview

A 13-month, 28-day-per-month calendar beginning December 19 each year, with a playing card assigned to every regular day. Each day always maps to the same Gregorian date range regardless of leap year. Two special intercalary days sit outside the 364-day structure.

### Calendar structure

```
Cosmic Year XXXX
├── Begins      :  December 19 of year XXXX-1
├── 13 months × 28 days = 364 regular days
├── Feb 29      :  Intercalary day inside Month III → always 7♦
└── Leap Day    :  December 18 of year XXXX → Joker ★
```

The displayed year label is one ahead of the internal start year. "Cosmic Year 2026" runs December 19, 2025 through December 18, 2026.

### Month reference

| Month | Roman | Gregorian Range |
|---|---|---|
| 1 | I | Dec 19 – Jan 15 |
| 2 | II | Jan 16 – Feb 12 |
| 3 | III | Feb 13 – Mar 12 *(Feb 29 → 7♦ intercalary in leap years)* |
| 4 | IV | Mar 13 – Apr 9 |
| 5 | V | Apr 10 – May 7 |
| 6 | VI | May 8 – Jun 4 |
| 7 | VII | Jun 5 – Jul 2 |
| 8 | VIII | Jul 3 – Jul 30 |
| 9 | IX | Jul 31 – Aug 27 |
| 10 | X | Aug 28 – Sep 24 |
| 11 | XI | Sep 25 – Oct 22 |
| 12 | XII | Oct 23 – Nov 19 |
| 13 | XIII | Nov 20 – Dec 17 |
| ★ | Leap Day | Dec 18 → Joker |

### Card suit colours (terminal)

| Suit | Colour |
|---|---|
| ♠ Spades | Blue |
| ♦ Diamonds | Yellow |
| ♣ Clubs | Green |
| ♥ Hearts | Red |
| ★ Joker | Magenta |

Colour output is automatic when connected to a TTY and suppressed in pipes and files.

### CLI usage

```bash
python cosmic_calendar.py                       # today (default)
python cosmic_calendar.py today                 # today
python cosmic_calendar.py month 2026 7          # Month VII, Cosmic Year 2026
python cosmic_calendar.py year  2026            # full-year summary
python cosmic_calendar.py year  2026 --full     # summary + all month tables
python cosmic_calendar.py lookup 2028-02-29     # look up Feb 29
python cosmic_calendar.py lookup 2028-12-18     # look up the Leap Day
```

`year` prompts "Print full day-by-day tables?" unless `--full` is passed.

### Sample output — `today`

```
══════════════════════════════════════════════════════════════════════════
                          TODAY'S COSMIC DATE
══════════════════════════════════════════════════════════════════════════
  Gregorian Date  :  July 02, 2026
  Cosmic Year     :  Cosmic Year 2026 (Dec 2025 - December 2026)
  Cosmic Month    :  VII  (Jun  5 – Jul  2)
  Cosmic Day      :  28
  Card            :  K♥  (Hearts)
══════════════════════════════════════════════════════════════════════════
```

### Sample output — `month 2026 7` (truncated)

```
══════════════════════════════════════════════════════════════════════════
  Month VII  ·  Jun  5 – Jul  2  ·  Cosmic Year 2026 (Dec 2025 - December 2026)
══════════════════════════════════════════════════════════════════════════
  Day  │  Gregorian Date  │  Card    │  Suit        │  Notes
──────────────────────────────────────────────────────────────────────────
    1  │  Jun 05, 2026    │  A♠      │  Spades      │
    2  │  Jun 06, 2026    │  K♦      │  Diamonds    │
    3  │  Jun 07, 2026    │  Q♦      │  Diamonds    │
   ...
   28  │  Jul 02, 2026    │  K♥      │  Hearts      │  ◀ TODAY
──────────────────────────────────────────────────────────────────────────
★ Leap Day    Dec 18 · Joker · Dec 18, 2026
══════════════════════════════════════════════════════════════════════════
```

`◀ TODAY` highlights the current day when viewing the live month.

### Sample output — `lookup 2028-02-29`

```
══════════════════════════════════════════════════════════════════════════
                      LOOKUP  ·  February 29, 2028
══════════════════════════════════════════════════════════════════════════
  Cosmic Year     :  Cosmic Year 2028 (Dec 2027 - December 2028)
  Cosmic Position :  Intercalary Day — Feb 29
  Placement       :  Month III, between Days 16 & 17
  Card            :  7♦  (Diamonds)
══════════════════════════════════════════════════════════════════════════
```

### Sample output — `lookup 2028-12-18`

```
══════════════════════════════════════════════════════════════════════════
                      LOOKUP  ·  December 18, 2028
══════════════════════════════════════════════════════════════════════════
  Cosmic Position :  Leap Day  ·  Cosmic Year 2028 (Dec 2027 - December 2028)
  Card            :  Joker★
══════════════════════════════════════════════════════════════════════════
```

### Python API

```python
from cosmic_calendar import date_to_cosmic, cosmic_day_to_date, get_card
from datetime import date

# Locate any date
info = date_to_cosmic(date(1990, 6, 15))
# {'type': 'regular', 'cy': 1989, 'month': 7, 'day': 11,
#  'card': ('♦', '4'), 'greg': datetime.date(1990, 6, 15)}

# Convert cosmic position → Gregorian date
d = cosmic_day_to_date(cy=2025, month=7, day=1)   # → date(2026, 6, 5)

# Card for a cosmic position
suit, value = get_card(month=7, day=1)             # → ('♠', 'A')

# Feb 29 intercalary
date_to_cosmic(date(2028, 2, 29))
# {'type': 'feb29', 'cy': 2027, 'month': 3, 'day': 17, 'card': ('♦', '7'), ...}

# Leap Day
date_to_cosmic(date(2028, 12, 18))
# {'type': 'leap_day', 'cy': 2027, 'card': ('★', 'Joker'), ...}
```

`date_to_cosmic` returns `None` when the date falls outside any resolvable cosmic year window.

---

## 5. wealth\_algorithm.py

### Overview

An astrological wealth scoring engine. Given a birth date, time, and location it calculates ecliptic positions for 14 bodies, detects aspects using a custom metallic-ratio set, scores them by weight and orb tightness, applies dignity bonuses, and returns a normalised 0–100 wealth score.

### Custom rulerships

Two rulerships depart from tradition and propagate through detriment and fall tables automatically:

| Planet | Traditional | Custom addition |
|---|---|---|
| Venus | Taurus | **Virgo** |
| Mercury | Gemini | **Libra** |

### Metallic ratio constants

| Symbol | Name | Value | Derived aspect angle |
|---|---|---|---|
| φ | Golden | 1.6180339887… | 137.5078° |
| δ | Silver | 2.4142135624… | 61.7317° |
| β | Bronze | 3.3027756377… | 33.0025° |

### Aspect table

| Aspect | Angle | Orb | Score |
|---|---|---|---|
| Conjunction | 0.000° | 7.0° | +10.0 |
| Trine *(Supergolden)* | 120.000° | 6.0° | +9.0 |
| Golden Angle | 137.508° | 3°8′ | +8.0 |
| Sextile | 60.000° | 2.5° | +7.0 |
| Silver Angle | 61.732° | 3°8′ | +6.0 |
| Quintile | 72.000° | 2.0° | +5.0 |
| BiQuintile | 144.000° | 2.0° | +5.0 |
| Bronze Angle | 33.003° | 1°8′ | +5.0 |
| Semisextile | 30.000° | 1.0° | +3.0 |
| Opposition | 180.000° | 6.0° | −6.0 |
| Square | 90.000° | 5.0° | −5.0 |
| Semisquare | 45.000° | 1.5° | −3.0 |
| Sesquiquadrate | 135.000° | 1.5° | −3.0 |
| Quincunx | 150.000° | 1.5° | −2.0 |

**Scoring formula:**
```
Planet–Planet : base_score × avg_weight × orb_strength
Planet–Star   : base_score × avg_weight × orb_strength × 0.70
orb_strength  = 1 − (actual_orb / max_orb)
```

### Bodies tracked

**Planets (11):**

| Body | Weight | Notes |
|---|---|---|
| Jupiter | 10 | Highest wealth relevance |
| Venus | 9 | Rules Virgo (custom) |
| Pluto | 6 | |
| Sun | 6 | |
| Mercury | 5 | Rules Libra (custom) |
| Moon | 5 | |
| Saturn | 5 | |
| Uranus | 5 | |
| Mars | 4 | |
| Neptune | 4 | |
| True BML | 4 | True Black Moon Lilith (oscillating apogee) |

**Computed points (3):**

| Point | Weight | Formula |
|---|---|---|
| Lot of Fortune | 10 | Day: ASC + Moon − Sun · Night: ASC + Sun − Moon |
| Lot of Spirit | 8 | Day: ASC + Sun − Moon · Night: ASC + Moon − Sun |
| White Moon Selena | 6 | True BML + 180° |

*Lots use the Ptolemaic day/night reversal. Ascendant is Placidus.*

**Fixed stars (18) with weights:**

| Star | Wt | Star | Wt | Star | Wt |
|---|---|---|---|---|---|
| Sirius | 9 | Regulus | 9 | Aldebaran | 8 |
| Fomalhaut | 8 | Arcturus | 7 | Rigel | 7 |
| Vega | 7 | Kaus Australis | 6 | Altair | 6 |
| Sadalsuud | 6 | Betelgeuse | 6 | Antares | 5 |
| Zuben Elgenubi | 5 | Taygeta | 4 | Andromeda | 4 |
| Sabik | 4 | Rasalhague | 4 | Scheat | 3 |

### Dignity system

| Status | Multiplier | Symbol |
|---|---|---|
| Rulership | ×3.0 | ★ |
| Exaltation | ×1.5 | ▲ |
| Fall | ×−1.0 | ▼ |
| Detriment | ×−2.0 | ✗ |

### Sign modes

**Tropical 12-sign** (default) — equal 30° houses from 0° Aries.

**Sidereal 13-sign** (`--sidereal`) — IAU constellation boundaries corrected by the Lahiri ayanamsa. Ophiuchus (~247°–266° tropical) is the 13th sign.

### Score ratings

| Range | Label |
|---|---|
| 80–100 | Exceptional |
| 65–79 | Strong |
| 50–64 | Moderate |
| 35–49 | Developing |
| 0–34 | Challenging |

### CLI usage

```bash
python wealth_algorithm.py                                         # interactive prompts
python wealth_algorithm.py --name "Alice" --date 1990-06-15 \
    --time 14:30:00 --lat 40.7128 --lon -74.0060                  # scripted
python wealth_algorithm.py --date 1985-03-21 --time 08:00:00 \
    --lat 51.5074 --lon -0.1278 --sidereal --output result.json   # sidereal + export
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--name` | `Native` | Name of native |
| `--date` | *(prompted)* | Birth date `YYYY-MM-DD` (UTC) |
| `--time` | `12:00:00` | Birth time `HH:MM:SS` (UTC, 24-hour) |
| `--lat` | *(prompted)* | Latitude — North positive, South negative |
| `--lon` | *(prompted)* | Longitude — East positive, West negative |
| `--sidereal` | off | Lahiri sidereal + IAU 13-sign mode |
| `--top` | `40` | Number of top aspects to print |
| `--output` | none | Export path (`.json` or `.csv`) |
| `--ephe-path` | `ephe/` | Custom Swiss Ephemeris data directory |

---

## 6. wealth\_calendar\_algorithm.py — Integrated

### Overview

Merges both scripts into one self-contained file with a bridge layer that applies cosmic calendar modifiers to the wealth scoring engine. Calendar display works without `pyswisseph`; wealth scoring requires it.

### CLI — two top-level subcommands

```
python wealth_calendar_algorithm.py calendar <command>   calendar display
python wealth_calendar_algorithm.py wealth   [options]   wealth score
python wealth_calendar_algorithm.py [options]            wealth mode (default)
```

### Calendar subcommands

```bash
python wealth_calendar_algorithm.py calendar today
python wealth_calendar_algorithm.py calendar month 2026 7
python wealth_calendar_algorithm.py calendar year  2026
python wealth_calendar_algorithm.py calendar year  2026 --full
python wealth_calendar_algorithm.py calendar lookup 1990-06-15
python wealth_calendar_algorithm.py calendar lookup 2028-02-29
python wealth_calendar_algorithm.py calendar lookup 2028-12-18
```

### Wealth flags

Same as `wealth_algorithm.py` — `--name`, `--date`, `--time`, `--lat`, `--lon`, `--sidereal`, `--top`, `--output`, `--ephe-path`.

```bash
python wealth_calendar_algorithm.py wealth --date 1990-06-15 --time 14:30:00 \
    --lat 40.7128 --lon -74.0060 --name "Alice" --sidereal --output alice.json
```

### Wealth report structure

```
══════════════════════════════════════════════════════════════════════════════════
  WEALTH CALENDAR ALGORITHM  v3.0  ·  Alice
══════════════════════════════════════════════════════════════════════════════════
  Date / Time  : 1990-06-15  14:30:00 UTC
  Location     : N40.7128  W74.0060
  Mode         : Tropical · 12-Sign
────────────────────────────────────────────────────────────────────────────────

  COSMIC CALENDAR CONTEXT
  ─────────────────────────────────────────────────────────────────────────────
  Cosmic Year  : 1990
  Month        : VII  ·  Cancer  ·  Ruler: Moon  (+15% weight)
  Day          : 11
  Card         : 4♦  (Diamonds)
  Element      : Earth  ·  Boosts: Venus, Saturn, Mercury  (+10% weight)

  BODY                   LONGITUDE        SIGN        IN SIGN  DIG  R
  ────────────────────────────────────────────────────────────────────────
  Sun                    84.3812°  Gemini            24.38°
  Moon                  339.1204°  Pisces             9.12°
  ...

  FIXED STAR              LONGITUDE   WT
  ──────────────────────────────────────
  Sirius                 104.0831°    9
  Regulus                150.0012°    9
  ...

  DIGNITIES & DEBILITIES  (Venus→Virgo · Mercury→Libra)
  ▲  Jupiter         in Cancer      exaltation      +15.00
  ...

  TOP 40 ASPECTS BY WEALTH CONTRIBUTION
  Detected: 312 total  ( +198 harmonious  /  −114 tense )

  PAIR                                 ASPECT           ORB    STR    SCORE
  ──────────────────────────────────────────────────────────────────────────
  Jupiter / Lot of Fortune             Conjunction    0°50'3"  0.88  +88.10
  ...

  SCORE BY ASPECT TYPE
  Conjunction          +312.44  ████████████████████████
  Trine                +187.22  ██████████████
  ...

══════════════════════════════════════════════════════════════════════════════════
  ASPECT SCORE       :     +621.30
  DIGNITY BONUS      :      +15.00
  ────────────────────────
  RAW WEALTH SCORE   :     +636.30
  NORMALIZED (0–100) :        69.5
  RATING             :       Strong
══════════════════════════════════════════════════════════════════════════════════
```

---

## 7. Integration Bridge

The bridge layer connects the calendar to the scoring engine, running between body position calculation and aspect scoring.

### How it works

```
Birth date  ──►  date_to_cosmic()  ──►  cosmic position
                                              │
                                   get_cosmic_context()
                                              │
                        month → sign → month ruler  (+15% weight)
                        card suit → element → planet group  (+10% weight)
                                              │
                          apply_cosmic_weights(base_weights, ctx)
                                              │
                      score_aspects(planet_pos, boosted_weights, star_pos)
```

### Month ruler boost (+15%)

Each cosmic month maps to an IAU-aligned sign, which maps to a ruling planet. That planet's weight is multiplied by **1.15**.

| Month | Sign | Ruler |
|---|---|---|
| I | Capricorn | Saturn |
| II | Aquarius | Saturn |
| III | Pisces | Jupiter |
| IV | Aries | Mars |
| V | Taurus | Venus |
| VI | Gemini | Mercury |
| VII | Cancer | Moon |
| VIII | Leo | Sun |
| IX | Virgo | **Venus** ← custom |
| X | Libra | **Mercury** ← custom |
| XI | Scorpio | Pluto |
| XII | Ophiuchus | Pluto *(Chiron proxy)* |
| XIII | Sagittarius | Jupiter |

### Suit element boost (+10%)

The birth card's suit maps to a classical element, boosting an associated group of planets by **1.10**.

| Suit | Element | Planets boosted |
|---|---|---|
| ♠ Spades | Air | Mercury, Venus, Uranus |
| ♦ Diamonds | Earth | Venus, Saturn, Mercury |
| ♣ Clubs | Fire | Sun, Mars, Jupiter |
| ♥ Hearts | Water | Moon, Neptune, Pluto, True BML |

### Multiplicative stacking

```
Month-ruler only    →  weight × 1.15
Suit-planet only    →  weight × 1.10
Both                →  weight × 1.15 × 1.10  =  weight × 1.265
```

### Live example — 1990-06-15

Birth: **Cosmic Year 1990, Month VII (Cancer), Day 11, card 4♦ (Diamonds / Earth)**

```
  Planet              Base   Boosted   Note
  Sun                    6     6.000
  Moon                   5     5.750   +15%  ← month ruler (Cancer)
  Mercury                5     5.500   +10%  ← Earth suit (Diamonds)
  Venus                  9     9.900   +10%  ← Earth suit (Diamonds)
  Mars                   4     4.000
  Jupiter               10    10.000
  Saturn                 5     5.500   +10%  ← Earth suit (Diamonds)
  Uranus                 5     5.000
  Neptune                4     4.000
  Pluto                  6     6.000
  True BML               4     4.000
  Lot of Fortune        10    10.000
  Lot of Spirit          8     8.000
  White Moon Selena      6     6.000
```

### Special days

| Day type | Boost applied |
|---|---|
| Regular cosmic day | Month-ruler + suit-element |
| Feb 29 intercalary | Month III / 7♦ (Earth/Diamonds) — boosts applied normally |
| Leap Day (Dec 18) | None — no month or suit |

---

## 8. Output Formats & JSON Schema

### Console report

Always printed. Sections in order:

1. Header — name, date/time UTC, coordinates, sign mode
2. **Cosmic Calendar Context** *(integrated file only)* — year, month, sign, ruler, day, card, element, boosts applied
3. Body positions — longitude, sign, degree-in-sign, dignity symbol, retrograde flag
4. Fixed stars — longitude, weight
5. Dignities and debilities
6. Top N aspects — pair, aspect name, orb (DMS), orb strength, contribution
7. Score by aspect type — ASCII bar chart
8. Final score block — aspect total, dignity bonus, raw score, normalised score, rating

### JSON export (`--output file.json`)

```jsonc
{
  "meta": {
    "name":         "Alice",
    "datetime_utc": "1990-06-15T14:30:00",
    "latitude":     40.7128,
    "longitude":    -74.006,
    "mode":         "tropical_12sign"   // or "sidereal_lahiri_13sign"
  },

  "cosmic_context": {                   // integrated file only
    "type":              "regular",
    "cy":                1989,
    "cy_label":          1990,
    "month":             7,
    "month_roman":       "VII",
    "month_range":       "Jun  5 – Jul  2",
    "month_sign":        "Cancer",
    "month_ruler":       "Moon",
    "day":               11,
    "card_suit":         "♦",
    "card_suit_name":    "Diamonds",
    "card_value":        "4",
    "card_element":      "Earth",
    "card_suit_planets": ["Venus", "Saturn", "Mercury"],
    "is_feb29":          false
  },

  "bodies": {
    "Sun": {
      "lon":         84.3812,
      "sign":        "Gemini",
      "deg_in_sign": 24.38,
      "retro":       false
    }
    // Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune,
    // Pluto, True BML, Lot of Fortune, Lot of Spirit, White Moon Selena
  },

  "fixed_stars": {
    "Sirius": { "lon": 104.0831 }
    // … 17 more
  },

  "aspects": [
    {
      "pair":     "Jupiter / Lot of Fortune",
      "type":     "P-P",
      "aspect":   "Conjunction",
      "orb":      0.8341,
      "orb_dms":  "0°50'3\"",
      "strength": 0.881,
      "contrib":  88.1
    }
    // sorted descending by |contrib|; type is "P-P" or "P-S"
  ],

  "dignities": [
    {
      "planet":  "Jupiter",
      "sign":    "Cancer",
      "dignity": "exaltation",
      "bonus":   15.0
    }
  ],

  "score": {
    "raw":        636.30,
    "normalized": 69.5,
    "rating":     "Strong"
  }
}
```

### CSV export (`--output file.csv`)

Aspect log only — one row per detected aspect:

```
pair,type,aspect,orb,orb_dms,strength,contrib
```

---

## 9. Customisation & Tuning

All tunable values are top-level module constants — no sub-classing required.

### Weight boosts (bridge layer — integrated file only)

```python
MONTH_RULER_BOOST:  float = 1.15   # +15% for birth-month ruling planet
SUIT_ELEMENT_BOOST: float = 1.10   # +10% for birth-card element planets
```

### Star factor

```python
STAR_FACTOR = 0.70   # planet–star aspects score at 70% of planet–planet
```

### Normalisation window

```python
def normalize(raw, lo=-600.0, hi=1200.0): ...
```

After running a batch of known charts, set `lo` to the approximate 5th-percentile raw score and `hi` to the 95th-percentile.

### Planet weights

```python
PLANET_CATALOG = {
    "Jupiter": {"id": swe.JUPITER, "weight": 10},
    "Venus":   {"id": swe.VENUS,   "weight":  9},
    ...
}
COMPUTED_WEIGHTS = {
    "Lot of Fortune": 10,
    "Lot of Spirit":   8,
    "White Moon Selena": 6,
}
```

### Aspect orbs and scores

```python
ASPECTS["Golden Angle"]["orb"]   = 2.0    # tighten the orb
ASPECTS["Trine"]["score"]        = 10.0   # raise the Trine score
```

### Custom rulerships

`RULERSHIPS` drives all detriment and fall tables automatically. Changing a rulership there propagates everywhere.

---

## 10. Module Structure

### cosmic\_calendar.py (576 lines)

```
[Card system]       CARD_VALUES, SUIT_SYMBOL, SUIT_NAME, MONTH_SEGMENTS, ROMAN, MONTH_RANGES
[ANSI colours]      class C, SUIT_COLOUR, coloured()
[Core logic]        is_greg_leap(), cosmic_year_start(), cosmic_day_to_date(),
                    leap_day_date(), get_card(), date_to_cosmic()
[Formatting]        WIDTH, fmt_card(), fmt_date(), fmt_cosmic_year()
[Display]           print_today_info(), print_month_calendar(),
                    print_year_summary(), print_lookup()
[CLI]               build_parser(), main()
```

### wealth\_algorithm.py (834 lines)

```
[Constants]         PHI, DELTA, BETA, GOLDEN/SILVER/BRONZE_ANGLE
[Aspect table]      ASPECTS  (14 aspects)
[Planet catalog]    PLANET_CATALOG, COMPUTED_WEIGHTS
[Star catalog]      STAR_CATALOG, STAR_FALLBACKS
[Zodiac systems]    SIGNS_12, _13SIGN_TROP, sign_tropical(), sign_sidereal_13()
[Dignity system]    RULERSHIPS, EXALTATIONS, DETRIMENTS, FALLS, planet_dignity()
[Formatting]        _dms(), _coord(), _log_entry()
[Ephemeris]         setup_ephemeris(), get_julian_day()
[Positions]         calc_planets(), calc_ascendant(), is_day_chart(),
                    calc_lots(), calc_selena(), calc_stars(), all_body_positions()
[Aspect engine]     short_arc(), detect_aspects(), orb_strength()
[Scoring]           score_aspects(), score_dignities(), normalize(), rating_label()
[Export]            export_results()  →  .json / .csv
[Report]            print_report()
[CLI]               _build_parser(), _prompt(), main()
```

### wealth\_calendar\_algorithm.py (1,600 lines)

```
[pyswisseph stub]   Lazy import — calendar mode works without the library
[Constants]         PHI, DELTA, BETA, angles (shared)
[Card system]       From cosmic_calendar.py (verbatim)
[ANSI colours]      From cosmic_calendar.py (verbatim)
[Core calendar]     From cosmic_calendar.py (verbatim)
[Display functions] From cosmic_calendar.py (verbatim)
[Aspect table]      From wealth_algorithm.py (verbatim)
[Planet catalog]    From wealth_algorithm.py (verbatim)
[Star catalog]      From wealth_algorithm.py (verbatim)
[Zodiac systems]    From wealth_algorithm.py (verbatim)
[Dignity system]    From wealth_algorithm.py (verbatim)
[Ephemeris]         From wealth_algorithm.py (verbatim)
[Scoring engine]    From wealth_algorithm.py (float weights for bridge compatibility)
[Bridge layer]      COSMIC_MONTH_SIGNS/RULERS, SUIT_ELEMENTS/PLANET_GROUPS,
                    get_cosmic_context(), apply_cosmic_weights()
[Export + report]   From wealth_algorithm.py + cosmic_context block added
[CLI dispatcher]    _run_calendar_mode(), _run_wealth_mode(), main()
```

---

## 11. Troubleshooting

**`pyswisseph not installed` when running wealth mode**

```bash
pip install pyswisseph
```

`cosmic_calendar.py` and the `calendar` subcommand of the integrated file work without it.

**`sefstars.txt` download fails on first run**

The script prints a warning and skips fixed stars. Download manually and place in `ephe/`:

```
https://github.com/aloistr/swisseph/raw/master/ephe/sefstars.txt
```

Or point to a directory that already contains it:

```bash
python wealth_algorithm.py --ephe-path /path/to/ephe ...
```

**A fixed star is skipped with `[!] not found`**

The star name didn't match any entry in `sefstars.txt`. The scripts try the primary catalog name then the fallback in `STAR_FALLBACKS`. Add a mapping to fix it:

```python
STAR_FALLBACKS["My Star"] = "AlternateName"   # sefstars.txt identifier
```

**Wrong cosmic position for a date near December 18 or 19**

The boundaries are exact: December 19 begins the new cosmic year; December 18 is always the Leap Day. All date arithmetic is calendar-date only (no time zones). A birth near midnight in a western timezone may fall on a different Gregorian date once converted to UTC, shifting the cosmic position.

**Score is unexpectedly high or low**

The normalisation window (`lo=−600`, `hi=1200`) may not suit your sample. Run the algorithm on a batch of known charts and adjust `normalize()` to cover the observed raw score range.

**`date_to_cosmic` returns `None`**

The search window covers `±1` year relative to the input. Dates far outside the supported range return `None`. All dates from roughly 1700 to 2300 resolve without issue.

**`year` subcommand hangs waiting for input**

Pass `--full` to skip the interactive prompt and print all month tables immediately:

```bash
python cosmic_calendar.py year 2026 --full
python wealth_calendar_algorithm.py calendar year 2026 --full
```

---

*cosmic\_calendar.py · wealth\_algorithm.py · wealth\_calendar\_algorithm.py v3.0*
*Metallic-Ratio Aspects · Cosmic Playing Cards · Venus → Virgo · Mercury → Libra*#   W e a l t h - A l g o r i t h m  
 #   W e a l t h - A l g o r i t h m  
 