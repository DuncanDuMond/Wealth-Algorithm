# Wealth Algorithm Agent

Wraps `wealth_algorithm.py` + `cosmic_calendar.py` -- layered with a
64-Gate Human Design system, an Enneagram + MBTI typology overlay, a
Mayan Tzolkin calendar, a 15-cipher numerology ring, a Cosmic Playing
Card + Tarot system, and astrocartography (now with map rendering) -- in
an Anthropic API tool-calling loop.

## What's new: map rendering

`tools/astrocartography_map.py` + a new `render_astrocartography_map`
tool. Takes the same birth date/time as `get_astrocartography_lines` and
writes an actual world-map image (PNG or SVG) to disk instead of raw
coordinate lists -- the "next step" flagged in the previous version of
this README.

## Why a static image, not an interactive HTML map

This was a real choice, not the default option. An HTML file with an
embedded interactive map (Leaflet + OpenStreetMap tiles, or similar) was
the more obvious-sounding answer, and would need internet access only at
*view* time (in your browser), which is normal and would've been fine.
The actual reason it wasn't built that way: **this project has no way to
render or screenshot that kind of output to confirm it looks right
before shipping it** -- the sandbox this was built in can reach GitHub
and a handful of package registries, not arbitrary CDNs or map tile
servers, so an HTML/JS map would have shipped on faith that the Leaflet
API calls were right, not on having actually seen it render. A static
image, by contrast, could be -- and was -- generated and visually
inspected before you ever saw it, the same way the astro.com comparison
in the previous update was done. Given how much of this project has been
about checking things rather than trusting that they're probably fine,
that difference mattered more than interactivity did. An HTML/Leaflet
version remains a reasonable thing to add later; it just isn't a
straight upgrade from this version, it's a different tradeoff.

## What's bundled: a real, standard dataset, not hand-drawn coastlines

`data/world_boundaries.json` -- Natural Earth's public-domain 110m
country boundaries, the standard small-scale dataset used all over the
place for exactly this kind of world map, fetched from its GitHub
mirror and trimmed (coordinates rounded to 2 decimals, ~1km precision,
more than enough at world scale) from ~840KB down to ~170KB. No network
access needed at render time -- everything the map needs ships with the
project.

## Verified by actually rendering it, not just by the code compiling

Rendered the map for your real birth data and inspected it directly:
recognizable continents in correct positions, correct wraparound
handling at the +-180 degree seam (AC/DC curves split into separate
segments there instead of drawing a spurious line straight across the
map), and the same line-convergence pattern as the already-verified
coordinate data from the previous update. Also rendered a 3-body subset
specifically to confirm the `bodies` filter actually restricts what gets
drawn (it does) rather than just filtering the legend.

## Tool list (16 total)

| Tool | Purpose |
| --- | --- |
| `render_astrocartography_map` | Saves a PNG/SVG world map with the lines drawn on it; returns the file path |

`get_astrocartography_lines` (coordinate data) is unchanged and still
available for anything that wants the raw points instead of an image.

## Usage

```powershell
python main.py --direct 1994-03-21 14:30:00 40.7128 -74.0060 --render-map output/my_map.png
```

Or ask the agent directly -- "show me my astrocartography lines" now has
something to actually point at.

## Structure

```text
wealth_agent/
  tools/
    astrocartography_map.py   # new: renders lines onto a world map, matplotlib-based
  data/
    world_boundaries.json       # new: bundled Natural Earth 110m country boundaries
  agent_loop.py                  # +1 tool, extended system-prompt guidance
  main.py                          # +--render-map flag
  requirements.txt                   # +matplotlib
```
