---
name: tiny
description: Make a Tiny of any place - a pixel-art isometric diorama of a street, neighbourhood, campus or landmark, drawn from OpenStreetMap and painted tile by tile with the agent image generation (the user plan in Codex and ChatGPT, an OpenRouter key in other agents), and optionally published to Tiny World. Use when the user asks for a Tiny, a tiny city, a pixel-art or isometric map of a real place, or "@Tiny".
---

# Tiny

You turn any real place into a Tiny: one isometric pixel-art map the user can pan and zoom, made of square tiles you paint one by one.

The scripts live next to this file in `../../scripts/` (resolve the absolute path from this SKILL.md). They need `python3` with Pillow and numpy; if missing, install them for the user with `python3 -m pip install --user pillow numpy`.

## 0. Check Tiny World first (when TINY_WORLD is set or the user wants it public)

Tiny World is the shared map of Tiny cities. Before drawing, ask where this place belongs:

```
python3 <scripts>/hub.py where "<place, city>"
```

- `official`: the whole city is already a Tiny city (São Paulo, Barcelona). Do not start it again; tell the user and offer to help paint that city instead (last section).
- `duplicate`: this exact place is already painted. Tell the user who painted it and offer a place next to it.
- `grow` or `new`: go ahead; say in one line whether it joins a city or starts one.

If the user only wants a Tiny on their own computer, skip this step.

## 1. Draw the base

Pick a short folder name for the place under `~/Tiny/` (e.g. `~/Tiny/largo-da-batata`). Radius: 260 m by default (11 tiles to paint, about 15 minutes); 180 m for a single street corner (about 8 tiles); up to 400 m if the user asks for something bigger. The base always adds a 100 m margin around the radius where the city keeps going and then fades into fog and clouds, so the Tiny never ends on an empty edge.

```
python3 <scripts>/base.py "<place, city>" <radius_m> ~/Tiny/<name>
```

It geocodes the place, downloads (for the radius plus the margin) buildings, streets, parks, water and trees from OpenStreetMap (can take up to a minute), and writes `base.png`, `tiles/<id>.png` and `plan.json` (tiles sorted from the centre outwards). Tell the user in one line what was found: the place name and number of buildings and tiles. If it says the OpenStreetMap servers are busy, tell the user in one line and run the same command again (it caches nothing until it succeeds); give up only after three tries. Then build the viewer right away and open it beside the chat, so they watch the map fill in:

```
python3 <scripts>/stitch.py ~/Tiny/<name>
```

Open `~/Tiny/<name>/index.html` (in-app browser or the user's browser).

## 2. Paint every tile

No image generation tool in this agent (Claude Code, Cursor and others)? Paint with an API key instead: tell the user it costs about US$0.04 to 0.06 per tile, then run `OPENROUTER_API_KEY=... python3 <scripts>/paint_api.py ~/Tiny/<name>` and go to step 3.

Copy `<scripts>/prompt.txt` to the folder. For each tile in `plan.json` order, skipping ones already in `gen/` and ones with `"fog": true` (they sit entirely in the fog and are never painted):

1. Call the built-in image generation tool ONCE as an edit of exactly one input image, `tiles/<id>.png`, with the prompt from `prompt.txt` verbatim. Only the one base tile: extra reference images make the geometry drift.
2. Copy the generated PNG to `gen/<id>.png`.
3. Run `stitch.py` again and reload the viewer, so the new tile appears. Say one short line ("3/8 · the Largo itself is in").

Do not open or describe the images to yourself between tiles; it wastes the user's plan. If one tile fails, retry it once, then move on and list it at the end.

If the user wants to keep using Codex while it paints, run the whole loop in the background instead:

```
<scripts>/paint.sh ~/Tiny/<name> 2
```

It paints the missing tiles with `codex exec`, two at a time, and restitches after each one.

## 3. Finish

Run `stitch.py` a last time. Its output lists `repintar`: tiles that drifted from the real geometry (`corr_base` under 0.25 in `qa.json`, ignoring tiles that are mostly fog). Repaint each of those once, saving the new image as `gen/<id>-2.png` (keep the first one): `stitch.py` compares every version of a tile and keeps the one closest to the real geometry. Dense centres often score 0.15-0.25 with sharp detail; one repaint is enough. Show the user `tiny.png` and the viewer, with the number of tiles and how long it took. That is their Tiny; it stays on their computer unless they publish it.

## 4. Publish to Tiny World (only when the user asks)

Tiny World is the public map where every Tiny lives, next to Tiny São Paulo and Tiny Barcelona; a place in a city that is already there joins that city. Publish only when the user asks ("publish it", "put it on Tiny Cities"); the upload is public. Ask what name to sign it with if they have not said (default: anonymous).

```
python3 <scripts>/hub.py publish ~/Tiny/<name> --by "<their name>"
```

It uploads the painted tiles (never the user's files or anything else), waits while Tiny World redraws the place from OpenStreetMap and checks the painting against the real streets (a few minutes), and prints `{"status": "live", "url": ...}`. Give the user the link. If it prints `rejected`, tell them the reason in `why` in one line; the usual fix is repainting the tiles listed by `stitch.py` and publishing again.

## Help paint a city that is already there

When the user asks to "help paint São Paulo" (or another city listed by `python3 <scripts>/hub.py cities` with `"help": true`), you paint tiles of the big shared map with their plan. Ask how many tiles they want to give (default 5; each takes one to three minutes). For each one:

1. `python3 <scripts>/hub.py next sao-paulo ~/Tiny/_help --by "<their name>"` prints the tile, `images_in_order` and `prompt_file`.
   If they picked a tile on the map ("paint tile 33_-50 of São Paulo"), add `--tile 33_-50` and paint only that one; if the answer says it is taken, tell them and offer the next free tile.
2. Call your image generation tool ONCE (or run paint_api.py --job ~/Tiny/_help, which writes painted.png there) with exactly those images in that order (the last one is the base to redraw; the others are style references) and the prompt from `prompt_file` verbatim.
3. `python3 <scripts>/hub.py submit ~/Tiny/_help <generated.png>` with the PNG exactly as generated (no crop, no resize). It answers `"ok": true` or `why`. If refused, repaint that tile once (run `next` again; it hands back the same tile) and move on after a second refusal.

Say one short line per tile ("2/5 · accepted"). At the end tell them how many of their tiles were accepted (`painted_by_you`); accepted tiles go into the city's next expansion.

