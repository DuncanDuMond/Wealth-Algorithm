# Wealth Algorithm Agent

Wraps your `wealth_algorithm.py` + `cosmic_calendar.py` in an Anthropic API
tool-calling loop, so the system can be driven conversationally ("what's my
wealth score", "compare that to my partner's", "what card was I born
under") instead of as separate single-shot CLI runs.

## Fidelity: this is a port, not a reinterpretation

`tools/chart.py`, `tools/scoring.py`, and the core of `tools/calendar_bridge.py`
are direct ports of your two uploaded scripts -- same constants, same
formulas, same tables. This was checked, not assumed:

- **wealth_algorithm.py**: I ran your actual uploaded script (`--date
  1994-03-21 --time 14:30:00 --lat 40.7128 --lon -74.0060 --sidereal`) and
  compared against the ported version for the same input. Raw score, dignity
  bonus, normalized score, rating, and individual aspect log entries
  (orb-to-the-arcsecond, strength, contribution) all matched exactly.
- **cosmic_calendar.py**: I ran your actual reverse lookup (`date_to_cosmic`)
  against every single day across 2024-2027 (1,461 days, spanning leap
  years, Joker Days, and Feb 29) and the forward lookup (`cosmic_day_to_date`
  + `get_card`) across 5 cosmic years x 13 months x 28 days (1,820
  combinations). Zero mismatches against your source in either direction.

The one thing that's **not** a port: the wealth-score <-> calendar
*integration* layer (month-ruler and suit-element boosts). That logic lives
in a merged script you mentioned building previously but hasn't been
uploaded here -- see "What's still scaffolding" below.

## Framework: true sidereal only

Your `wealth_algorithm.py` defaults to **tropical** and takes `--sidereal`
to opt in. Per your standing instruction for this project, `get_natal_chart`
is hardcoded to `sidereal=True` throughout the agent layer -- it's never
exposed as a choice to the model. `tools/chart.py` still contains the
tropical code path (it's in your source), but nothing in `agent_loop.py`
or `main.py` can trigger it.

## Setup

```powershell
pip install -r requirements.txt --break-system-packages
$env:ANTHROPIC_API_KEY = "your-key-here"    # current PowerShell session
```

`tools/chart.py` auto-downloads `ephe/sefstars.txt` (fixed-star data) on
first use, exactly like your original `setup_ephemeris()`. Everything else
(the 10 classical planets + True BML) runs on Swiss Ephemeris's built-in
analytical fallback with no data files needed.

## Running it

```powershell
# Test the astrology/scoring pipeline directly -- no API key, no API cost
python main.py --direct 1994-03-21 14:30:00 40.7128 -74.0060

# Full conversational agent
python main.py
```

```
you> What's the wealth score for someone born 1994-03-21 2:30pm UT in New York (40.7128, -74.0060)? Call them "self".
agent> [computes chart + score, explains the result in plain language]

you> What card was that person born under on the cosmic calendar?
agent> [calls date_to_cosmic_day, answers using the already-known birth date]
```

## Structure

```
wealth_agent/
  tools/
    chart.py            # PORTED: positions, ascendant, Lots, Selena, stars
    scoring.py           # PORTED: aspects, dignities, normalize, rating
    calendar_bridge.py   # PORTED (dates/cards) + SCAFFOLDED (boosts)
  agent_loop.py           # Anthropic API tool-use loop + WealthAgent class
  cache.py                # pathlib-based local JSON cache for chart lookups
  main.py                 # CLI: --direct mode or interactive agent
  requirements.txt
```

Run everything from inside this directory (`tools/` is a subpackage;
`agent_loop.py`, `cache.py`, `main.py` are plain sibling modules).

## What each tool does

- **get_natal_chart** — sidereal chart: 11 tracked bodies (10 planets +
  True Black Moon Lilith), 3 computed points (Lot of Fortune, Lot of
  Spirit, White Moon Selena), 18 fixed stars, Placidus ascendant, day/night
  status. Stores under a label; checks the local disk cache first.
- **score_wealth** — reads a stored chart by label, runs your exact aspect
  engine (14 aspect types incl. Golden/Silver/Bronze metallic-ratio angles,
  Planet-Planet + Planet-Star with the 0.70 star factor) and dignity system
  (Venus rules Virgo, Mercury rules Libra), normalizes to 0-100 with a
  rating label, and **automatically** applies the Cosmic Calendar
  month-ruler/suit-element boosts based on the chart's birth date.
- **cosmic_day_to_date** / **date_to_cosmic_day** — forward/reverse
  calendar lookups, usable standalone. Both take/return the *label* form of
  the cosmic year (what you'd actually say -- "Cosmic Year 2026"), matching
  your CLI's convention, even though your source's internal functions use
  `cy` = label-1.
- **recall_chart** / **list_recalled_charts** — session memory, so "now
  compare that to Jan's chart" doesn't require re-sending birth data.

## What's still scaffolding (not in either uploaded file)

`tools/calendar_bridge.py`'s `COSMIC_MONTH_RULERS` and `SUIT_PLANET_GROUPS`
power the two multiplicative boosts. Neither table exists in
`wealth_algorithm.py` or `cosmic_calendar.py` -- you mentioned building this
integration in a separate merged script previously, but that file hasn't
been uploaded here. Current state:

- **Boost values (1.15x month ruler, 1.10x suit element, stacking
  multiplicatively)** — match what you described building before, so
  these are probably right.
- **COSMIC_MONTH_RULERS** — *derived*, not guessed: for each cosmic
  month's Gregorian midpoint, I ran your actual `sign_sidereal_13()` with
  the live ayanamsa and looked up that sign's ruler in your actual
  `RULERSHIPS` table. Grounded in your two real scripts, just not
  something you wrote directly. One quirk worth knowing: Month XIII
  (Ophiuchus) can never trigger this boost, because Chiron -- Ophiuchus's
  traditional ruler -- isn't a tracked/scored body in `wealth_algorithm.py`
  at all (it only appears as a comment). I left it documented-but-inactive
  rather than inventing a Chiron position your source doesn't compute.
- **SUIT_PLANET_GROUPS** — genuinely invented. Common Tarot-suit/element
  correspondence (Clubs/Wands=Fire, Diamonds/Pentacles=Earth,
  Spades/Swords=Air, Hearts/Cups=Water) mapped to the classically
  associated planets. Zero grounding in anything you've shared.

If you have the actual merged integration script, upload it and I'll
replace both tables with your real ones.

## Two bugs from the previous scaffolded version, now moot

The prior version of this project (before you uploaded the real scripts)
had a gap in its sign-boundary table and a Dec-17 year-boundary bug in its
own guessed calendar logic. Both were in code that's now fully replaced by
your verified originals, so there's nothing to carry forward -- flagging
only so the fix history isn't a mystery if you compare against earlier
output.