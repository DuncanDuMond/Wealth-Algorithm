# Wealth Algorithm Agent

Wraps `wealth_algorithm.py` + `cosmic_calendar.py` -- layered with a
64-Gate Human Design system, an Enneagram + MBTI typology overlay, a
Mayan Tzolkin calendar, and now a 15-cipher numerology ring -- in an
Anthropic API tool-calling loop.

## What's new: numerology

`tools/numerology.py`, a faithful port of your uploaded `numerology.py`
(15 active ciphers -- Agrippa Key, phi, pi-3.144, e, root-3, root-10,
silver/supersilver, Emerald/Copper/Nickel metallic means, Francis Bacon,
supergolden, Iron, bronze -- each mapped to a Chaldean 1-9 planetary
ruler). `get_natal_chart` takes one more optional field,
`numerology_name`, GIVEN like enneagram_type/mbti_type. A new
`get_numerology_profile` tool works standalone, no chart needed.

**This one is different from every other boost tier.** Gates, Typology,
and the Calendar all multiply the already-normalized 0-100 score.
Numerology doesn't -- it's **additive, folded into the raw score before
normalization**, exactly matching what your own `wealth_algorithm.py`
does in its `main()`: `raw = asp_score + dig_bonus + num_boost`, then
`normalize(raw)`. Not a stylistic choice on this end -- that's genuinely
how your source computes it, discovered by reading the diff in your
uploaded file rather than assumed to match the existing pattern.
`scoring.py` needed a real structural change to support this cleanly (see
below), not just a new parameter.

## The one real gap: ciphers.js wasn't included

`numerology.py` reads the actual 26-letter-per-cipher values from an
external `ciphers.js` file at runtime -- that file is genuinely external
data this module doesn't generate, and it wasn't part of this upload.
Every function that needs it (`compute_numerology_profile`,
`score_numerology_boost`, the `get_numerology_profile` tool, and
`score_wealth`'s numerology tier) is fully ported and tested, but
produces nothing real without that file. Calling any of them right now
returns a plain, specific message naming the missing path -- never a
fabricated cipher table standing in for the real one. Drop a real
`ciphers.js` next to `ephe/` at the `wealth_agent/` root and everything
using it starts working with no code changes.

## What's verified, and how, given the file that matters most is missing

Every part of the engine that *doesn't* depend on the missing file was
checked directly against your actual source, not assumed correct because
the port looked right:
- `reduce_number`, `date_value`, and `ruling_planet` (including master-
  number handling: 29 -> 11, preserved as a master number, ruling through
  Moon via its un-preserved root 2) verified against hand-computed
  examples.
- The cipher parser, `compute_numerology_profile`, and
  `score_numerology_boost` were tested end-to-end against your *actual*
  uploaded `numerology.py` -- using a synthetic test-only cipher file
  (clearly labeled as such, never treated as real data) so the pipeline
  logic could be exercised without the real cipher values. That synthetic
  file deliberately reproduces the documented "e 2.71 has 27 values for
  26 letters" bug, to confirm the truncation fix in your source actually
  fires and matches exactly. Result: 0 mismatches across all 15 ciphers'
  raw sums, reduced values, and ruling planets, and the final boost value
  matched to the 12th decimal place, tested against a real chart's actual
  aspect/dignity logs.
- `score_wealth`'s new additive-boost math was checked arithmetically:
  the no-numerology raw score plus the computed numerology boost equals
  the with-numerology raw score, exactly, not approximately.

## A real architectural change, not just a new file

`numerology.score_numerology_boost()` needs the aspect/dignity logs
*before* the score is finalized -- it scales each cipher's ruling
planet's already-computed contribution, so it can't run after
`score_wealth()` returns, only in the middle of it. `scoring.py` now
splits that into `score_aspects()` + `score_dignities()` (already public)
feeding a new `finalize_wealth_score()`, with `score_wealth()` itself
becoming a thin convenience wrapper around all three for callers that
don't need numerology. Confirmed this didn't change anything for
existing callers: the same test chart from every prior verification in
this project still returns the identical raw score with no numerology
given.

## Tool list (13 total)

| Tool | Purpose |
|---|---|
| `get_numerology_profile` | Life path + all 15 ciphers for a name/date, no chart needed |

`get_natal_chart` gained `numerology_name` (optional). `score_wealth`
runs the numerology tier automatically whenever a chart has one set and
`ciphers.js` is present.

## Structure

```
wealth_agent/
  tools/
    numerology.py   # new: cipher ring, faithfully ported, ciphers.js required
    scoring.py        # score_wealth split into score_aspects+score_dignities+finalize_wealth_score
    chart.py           # +numerology_name field on NatalChart (given, not computed)
  agent_loop.py         # +1 tool, score_wealth dispatch restructured for the additive boost
  main.py                # --numerology-name / matches wealth_algorithm.py's own CLI flag
  ciphers.js              # NOT INCLUDED -- add your real file here to enable this tier
```
