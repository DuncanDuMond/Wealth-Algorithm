# Wealth Algorithm Agent

## Sidereal audit: complete

Following up on the `calc_stars()` bug found last update, every place in
this codebase that touches `swe.get_ayanamsa_ut()` or
`swe.set_sid_mode()` was checked -- not just the one that turned out to
be broken. Five call sites total: `calc_chiron_rahu_ketu`,
`all_body_positions`, and `gate_calendar_bridge.py`'s `day_gate()` all
already set the sidereal mode explicitly before reading the ayanamsa,
confirmed correct. `calc_ascendant` was the one with a real, if
currently-harmless, issue.

**`calc_ascendant` hardened, not because it was giving a wrong answer.**
It relied on some *earlier* call (`calc_planets`, in every actual code
path today) having already set the sidereal mode globally, since
`get_ayanamsa_ut()`'s result depends on whatever mode swisseph most
recently had set. That's correct today because `all_body_positions`
always calls `calc_planets` before `calc_ascendant` -- but it's an
implicit dependency, not a guaranteed one, and a future call site that
computed just the ascendant in isolation would have silently gotten a
wrong answer, not an error. Fixed by having it set the mode itself.
Confirmed this changes nothing about current behavior (same ascendant,
byte-for-byte, for the standing test chart) while confirming the
failure mode it closes: computed the ascendant in isolation after
deliberately setting the *wrong* prior mode, and it now self-corrects
instead of silently inheriting the wrong one.

## The three new errors: none of them are code bugs

Diagnosed by direct reproduction, not inference -- extracted a
completely clean copy of the current files and reran exactly what
produces each symptom:

- **`calendar_bridge` ModuleNotFoundError** -- your local
  `tools/gate_calendar_bridge.py` still has the old absolute import.
  Confirmed by diffing your traceback's line 52 against this project's
  line 28, which is `from . import calendar_bridge as cb` -- different
  line number, different import style. This file hasn't been replaced
  with what was delivered last update.
- **`Algorithm` ModuleNotFoundError** -- `import
  Algorithm.wealth_agent.tools.human_design_gates as hdg` is not a line
  this project has ever contained. "Algorithm" is the name of your
  OneDrive project folder, not a Python package -- this has the exact
  shape of an editor's "quick fix" auto-import suggestion built from a
  workspace-relative file path, most likely accepted while trying to
  resolve the first error. Your local `tools/gates.py` has been edited
  into something new and broken, not reverted to something old.
- **`chart.py`'s "attempted relative import with no known parent
  package"** -- reproduced this exactly, word for word, by running
  `python chart.py` from inside the `tools/` folder directly. This is
  standard, unavoidable Python behavior for any file using relative
  imports (`from . import X`) when it's executed directly instead of
  imported as part of its package -- not something fixable in the file
  itself, since the failure happens while Python is still processing
  the file's own import statements, before any code in the file (a
  main guard, a warning, anything) could run. This is almost certainly
  from an editor's "Run current file" button being used on `chart.py`
  (or some other file inside `tools/`) instead of running `main.py` or
  `agent_loop.py`.

**The fix for all three is the same, and it's not a code change**:
delete the local `wealth_agent/` folder entirely and replace it with a
fresh copy of what's delivered here, rather than patching individual
files -- there's no way to know from here which other local files might
also be stale or auto-edited. Then run only `python main.py` or `python
agent_loop.py`, only from the `wealth_agent/` root, never a file inside
`tools/` directly.

## New: every file in `tools/` now says so itself

Since this is the second round of exactly this kind of confusion, every
file in `tools/` now opens with an explicit note in its own docstring:
it's part of a package, it can't be run directly, and here's what to run
instead. Purely additive -- confirmed nothing compiles differently or
scores differently with these in place.

## Structure

Unchanged except:

```
wealth_agent/
  tools/
    chart.py    # calc_ascendant() now sets its own sidereal mode
    *.py        # every file: new "don't run this directly" docstring note
```
