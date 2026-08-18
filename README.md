# Wealth Algorithm Agent

Wraps `wealth_algorithm.py` + `cosmic_calendar.py` -- layered with a
64-Gate Human Design system, an Enneagram + MBTI typology overlay, a
Mayan Tzolkin calendar, a 15-cipher numerology ring, and now a Cosmic
Playing Card + Tarot system -- in an Anthropic API tool-calling loop.

## What's new: Cosmic Playing Cards + Tarot

`tools/cardology.py` and `tools/tarot.py`, copied in essentially
unchanged -- both are self-contained (Card in, profile out) with no
dependency on any other module in this project, so integration meant
building the bridge *to* them, not editing them. A new `get_cosmic_cards`
tool takes any date and returns the Earth card plus all 14 derived
"planetary" cards (Sun, Karma, Moon, Mercury...Phoenix) from the Master
Spirit/Life spreads, each with its Tarot equivalent.

**Never touches the score, in either direction.** This is explicit in
your own updated `wealth_algorithm.py` -- its `main()` computes
`raw = asp_score + dig_bonus + num_boost` with no card term at all, and
there's a comment in the source noting exactly where a scoring hook
*would* go if you ever define what a card/suit/arcana is worth. Nothing
here invents that definition. `get_cosmic_cards` is entirely separate
from `score_wealth`, the same relationship Mayan astrology already has
in this project.

## Verification, given both files came unusually well-documented already

Both uploaded files already carry their own confidence notes and a
`_run_self_test()` -- more thorough self-documentation than most of what's
been ported into this project so far. That's a reason to check carefully
rather than a reason to check less: both self-tests were run and pass,
and independent verification went further than what they check on their
own:

- Swept all 52 possible Earth cards through `derive_cosmic_cards()` --
  no errors, and confirmed the module's own 52-card-completeness
  assertions (Life spread and Spirit spread each form a genuine, non-
  duplicated deck) actually hold, not just that they're asserted.
- The demo output happens to show Sun and Neptune landing on the same
  card for one specific Earth card (Queen of Hearts) -- checked whether
  that's a systematic bug by sweeping all 52 Earth cards and tabulating
  every field-pair coincidence. It's ordinary chance, spread thinly
  across many different field-pairs (no pair dominates), not a pattern.
- Swept all 52 real playing cards through `tarot_equivalent()` /
  `cosmic_card_number()` and confirmed the 1-52 cosmic numbering is a
  clean bijection, with 0 and 53 correctly left unused by any real card
  (reserved for the two Jokers).
- Cross-validated the full chain -- date -> Earth card -> cosmic profile
  -> Tarot profile -- against your actual uploaded `wealth_algorithm.py`
  (using its real `birth_card_str()` and the `cosmic_calendar.py` from an
  earlier upload) for the same test date used throughout this project.
  Exact match on every field.

**What independent verification can't resolve**: the module's own KARMA
table is flagged (by its author, not by this pass) as the least-verified
part of the source -- the smallest print on the chart, with only one
independently-confirmed cell. That's a transcription-accuracy question
against a source image this project doesn't have; no amount of internal
consistency-checking closes that gap, so the caveat is carried forward
as-is rather than either repeated without checking or quietly dropped.

## New bridge function: `birth_card_str()`

wealth_algorithm.py's own version converts a `cosmic_calendar.date_to_cosmic()`
result into cardology's compact notation ('QH', '10C', ...). This
project's version in `agent_loop.py` does the same thing using
`calendar_bridge.date_to_cosmic_day()` instead of a standalone
`cosmic_calendar` import -- same suit-symbol translation table, same
"returns None on the cosmic Leap/Joker Day" behavior, confirmed to
produce identical output to the original for every date checked.

## Tool list (14 total)

| Tool               | Purpose                                                          |
|--------------------|------------------------------------------------------------------|
| `get_cosmic_cards` | Earth card + 14 derived cards + Tarot equivalents for any date   |

## Structure

```text
wealth_agent/
  tools/
    cardology.py   # new: Master Spirit/Life spreads, copied in unchanged
    tarot.py         # new: playing-card <-> Tarot mapping, one import path fix
  agent_loop.py       # +1 tool, +birth_card_str() bridge, +1 system-prompt paragraph
  main.py               # --direct output includes cosmic_cards automatically
```
