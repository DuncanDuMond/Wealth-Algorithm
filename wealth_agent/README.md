# Wealth Algorithm Agent

This update is the largest single pass on this project so far -- a real
ciphers.js, the long-missing house system, three new tracked bodies, an
extended 15-body dignity table, six new numerology calculations, and a
new Enneagram/MBTI input format with a startup prompt to collect it.

## The real ciphers.js is bundled, finally

`ciphers.js` now ships in the project root (the default path
`tools/numerology.py` already looked for). Every "ciphers.js not found"
gap flagged in earlier versions is closed -- `get_numerology_profile`,
`get_core_numerology_profile`, and `score_wealth`'s numerology tier all
produce real numbers now, not graceful-skip messages. Verified against
the real file, not just checked for existence: parsing it found all 15
of the irrational-constant ciphers this project's numerology ring
expects, the documented "e 2.71 has 27 values for 26 letters" fix fired
against real data (not just the synthetic test file used previously),
and a genuine parser bug got caught in the process -- the file opens
with a commented-out template example wrapped in `/* */`, which the
existing comment-stripping only handled for `//` line comments. Fixed
before it could silently mismatch a real cipher against the template.

## House system: the gap since the very first version is closed

`wealth_algorithm_updated_house_system.py` has a real `HOUSES` table
and `house_of_sign()`/`house_for_longitude()` -- ported into
`tools/chart.py`, and every "house": null placeholder that's existed
since the first version of this project (with a TODO pointing at
exactly this) now returns a real house number. Whole-sign houses,
House 1 = Sagittarius (matching the Cosmic Calendar's own year start),
House 12 covering both Scorpio and Ophiuchus.

## Three new tracked bodies: Chiron, Rahu, Ketu

Added specifically so their dignities (below) could be evaluated --
Rahu/Ketu use the mean lunar node (standard in sidereal/Vedic
astrology), Chiron needed a second ephemeris file (`seas_18.se1`,
fetched automatically now, same source as the existing `sefstars.txt`)
since the main 10 planets silently fall back to a built-in
approximation when their files are missing but Chiron has no such
fallback -- confirmed directly: an earlier version of this fetch didn't
include it, and `calc_ut`'s own error named the missing file.

**Deliberately kept out of aspect scoring.** Chiron/Rahu/Ketu's
positions feed dignity evaluation only, through a separate code path
from the 10 classical/modern planets -- not `chart.positions`, which
`score_aspects` iterates over for every planet-planet and planet-star
pair. Adding them there would have silently expanded aspect scoring to
many new pairs using an invented weight, which is a bigger change than
"evaluate their dignities" and wasn't asked for.

## Dignity table extended to 15 bodies

Domicile/Exaltation/Detriment/Fall for all 10 classical/modern planets
plus Chiron/Rahu/Ketu/True BML/White Moon Selena, from the table given
in chat. Detriment/Fall for all 5 new bodies were checked against the
existing opposite-sign derivation rule before being trusted -- every
single one matched with zero exceptions, which is strong evidence the
table was transcribed correctly, not just a convenient shortcut.

**A real, substantive discrepancy was caught and resolved, not smoothed
over.** Mercury, Venus, and Neptune's exaltations in the new table
(Aquarius/Capricorn/Cancer) differ from what was already verified
against your actual uploaded source scripts in earlier sessions
(Virgo/Pisces/Leo). Rather than picking one silently, this was checked
against the new message's OWN "Dominant dignity architecture" per-sign
table -- which independently confirms all three new values ("Aquarius:
Mercury exaltation...", "Capricorn: Venus exaltation...", "Cancer:
...Neptune exaltation"). That's convergent, self-consistent evidence
within your own message, stronger than either table alone, so the new
values are what's implemented -- flagged here rather than silently
overwritten.

`SIGN_DIGNITY_ARCHITECTURE` (the per-sign summary) is DERIVED
programmatically from the planet-level table above, not hand-typed a
second time -- and checked against your literal wording sign-by-sign
before being trusted. One real finding from that check: your summary
for Leo says "Mercury & Uranus detriment," but Mercury's actual
placement there is a fall (Uranus's is a genuine detriment) --
`DIGNITY_SCORE` weights these differently (-1.0 vs -2.0), so the
precise technical distinction from the planet table is what's
implemented, not the loosely-worded summary. Ophiuchus's entry ("Serpent
Gate / Transmutation") is carried over as the plain thematic label
given for it, since no planet has any dignity there to derive from.

## Six new numerology calculations, using your real Pythagorean cipher

Attitude, Expression, Soul Urge, Personality, and Maturity Numbers, plus
Universal Day/Month/Year and Personal Day/Month/Year -- all per the
exact formulas given in chat, including which ones do and don't preserve
master numbers (Attitude is the one deliberate exception: single-digit
only, every other number keeps 11/22/33/44). Every formula was hand-
verified against independently computed expectations before being
trusted, not just run once and assumed correct -- see the test run in
chat for the worked examples (Attitude, Expression/Soul Urge/Personality
with a simple two-letter test name, Universal Day/Month/Year including a
case that lands on a master number).

**Uses your real ciphers.js, not a hand-typed table.** Expression/Soul
Urge/Personality need the standard Pythagorean letter table (A=1..I=9,
J=1..R=9, S=1..Z=8) -- confirmed via independent web search to be the
correct standard before trusting it, then found as an entry literally
named "Pythagorean" in your real ciphers.js with exactly those values.
Extracted from there directly (`load_pythagorean_cipher`) rather than
typed out separately, and kept fully isolated from the existing
15-cipher irrational-constant ring -- confirmed 'Pythagorean' never
leaks into that ring's `ACTIVE_CIPHERS` whitelist, which would have
silently changed its `avg_weight` and the wealth-score boost it
produces.

New tool: `get_core_numerology_profile` (name + birth date, target_date
optional -- defaults to birth date, or pass any date for that date's
Personal Day/Month/Year). Not wired into `score_wealth` -- distinct from
the existing 15-cipher ring, which stays wired in unchanged.

## New Enneagram/MBTI input format, with a startup prompt

`get_natal_chart`'s `enneagram_type`/`mbti_type` now take the format
described in chat: `"7w8"` (wing, must be numerically adjacent to the
core -- checked, not just accepted), `"9"` (core only), or `"N/A"` for
Enneagram; `"INTJ-A"`/`"INTJ-T"` (Assertive/Turbulent) or `"INTJ"` for
MBTI. Wing and A/T variant are stored (`enneagram_wing`, `mbti_variant`)
but not scored -- no resonance mechanic was specified for them, only for
the core type/code, so nothing was invented for the rest.

`main.py`'s agent mode now prompts for both at startup (`--skip-typology-prompt`
to skip), validating with the same parsing the tool itself uses, so
input accepted at the prompt is guaranteed valid downstream too.

## Tool list (18 total)

| Tool                          | Purpose                                                                                   |
|-------------------------------|-------------------------------------------------------------------------------------------|
| `get_core_numerology_profile` | Attitude/Expression/Soul Urge/Personality/Maturity + Universal/Personal Day/Month/Year   |

## Structure

```text
wealth_agent/
  ciphers.js                        # new: real cipher data, resolves the long-standing gap
  tools/
    chart.py                          # +house system, +Chiron/Rahu/Ketu, new Enneagram/MBTI string parsing
    scoring.py                        # dignity table extended to 15 bodies, +SIGN_DIGNITY_ARCHITECTURE
    numerology.py                     # +6 calculations, +Pythagorean cipher loader (isolated from the 15-cipher ring)
    typology.py                       # +parse_enneagram_input, +parse_mbti_input
    gates.py / gate_calendar_bridge.py  # house TODOs resolved -- real values, not None
  agent_loop.py                       # +1 tool, extensive system-prompt updates
  main.py                             # +interactive typology prompt, updated --enneagram/--mbti formats
```
