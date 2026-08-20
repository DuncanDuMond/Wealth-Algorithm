# Wealth Algorithm Agent

Wraps `wealth_algorithm.py` + `cosmic_calendar.py` -- layered with a
64-Gate Human Design system, an Enneagram + MBTI typology overlay, a
Mayan Tzolkin calendar, a 15-cipher numerology ring, a Cosmic Playing
Card + Tarot system, and now astrocartography -- in an Anthropic API
tool-calling loop.

## What's new: astrocartography

`tools/astrocartography.py` implements the Jim Lewis AstroCartoGraphy
system directly -- MC/IC (meridian) and AC/DC (curved rising/setting)
world-map lines for each of the 10 classical/modern planets, from a
birth date/time alone. A new `get_astrocartography_lines` tool takes no
location at all -- that's the point of ACG: birth time is fixed, and the
lines are what solve for location.

**This one has no source script.** Every other module in this project
started as an uploaded file to port and verify against. This one is a
direct implementation of standard celestial-mechanics formulas -- the
same ones Jim Lewis's original system runs on, still used by every
modern ACG tool including astro.com's World Map -- which meant
verification had to work differently: instead of diffing against a
source file, every line this module produces was checked against
pyswisseph's own independent rise/set/transit solver (`swe.rise_trans`),
a completely separate code path from the trigonometry this module
implements.

## Independent of sidereal/tropical

Worth calling out since it's a real departure from every other module
here: ACG lines come from a planet's true equatorial position (right
ascension + declination) at the birth instant -- physical geometry.
Sidereal vs. tropical only changes which zodiac sign a longitude gets
labeled with; it doesn't move the planet. The lines would come out
identical either way, so this module doesn't have a sidereal setting,
and `agent_loop.py`'s guidance is explicit that the model shouldn't
frame this feature as either one.

## Verification, and a real bug it caught

Checked against `swe.rise_trans` for a real chart (your birth data --
confirmed against the astro.com World Map export you provided) across
all 10 bodies, all four line types, latitudes -89 to 89: 302+ points
checked, max discrepancy 0.03-0.15 seconds -- floating-point noise.
Circumpolar-gap detection (where a planet never crosses the horizon at a
given latitude, so the AC/DC curve has a real break) was checked the
same way: `rise_trans`'s own "event not found" code compared against
this module's gap ranges at 20 gap-midpoint latitudes, zero mismatches.

**The verification caught a real bug, not just confirmed correctness.**
The first version used geocentric coordinates throughout and matched
`rise_trans` almost exactly for every body -- except the Moon, where
AC/DC points were off by up to 3,537 seconds (nearly an hour, close to
15 degrees of longitude at Earth's rotation rate). Cause: the Moon is
close enough to Earth that its true position depends measurably on
*where on Earth's surface* you're standing -- topocentric parallax
reaches about 1 degree for the Moon, vs. arcseconds (negligible) for the
Sun and planets. AC/DC curves solve for exactly that surface location,
so geocentric coordinates were the wrong input specifically for the
Moon. Fixed with a short fixed-point iteration -- estimate a point
geocentrically, recompute the body's position as seen from that
candidate point, refine, repeat (converges in 1-2 steps) -- applied to
every body uniformly rather than special-cased to the Moon, since the
iteration costs nothing extra where parallax is already negligible.

Separately, spot-checked qualitatively against your astro.com export for
the same birth data (not pixel-precisely -- reading exact coordinates off
a static image isn't reliable): same dense line-convergence cluster over
central-northern Asia in both, same western vertical-line grouping, same
overall curve shapes.

## Not scored, same as Mayan and Cosmic Cards

No source script exists to check a scoring hook against, and there's no
reason to assume one should be invented. `get_astrocartography_lines` is
completely separate from `score_wealth`.

## Circumpolar gaps are real astronomy, not missing data

At some latitudes, a given planet never crosses the horizon at all
(circumpolar). The AC/DC curve genuinely breaks there -- `ac_circumpolar_gaps`
/ `dc_circumpolar_gaps` report those ranges explicitly rather than
silently interpolating a false continuous line through them.

## Tool list (15 total)

| Tool | Purpose |
| --- | --- |
| `get_astrocartography_lines` | MC/IC/AC/DC lines for all (or a subset of) planets, from birth date/time alone |

## Structure

```text
wealth_agent/
  tools/
    astrocartography.py   # new: Jim Lewis ACG lines, no source script -- verified via independent solver
  agent_loop.py             # +1 tool, +1 system-prompt paragraph
  main.py                     # --direct output includes astrocartography automatically
```

## Not built yet: map rendering

`get_astrocartography_lines` returns structured coordinate data (lists of
(longitude, latitude) points per line) -- deliberately, since this is a
backend Python tool, not a place to embed a mapping library. A world-map
visualization (matching what astro.com's own export shows) is a
reasonable next step if wanted, but is a separate scope decision from the
line-generation engine itself.
