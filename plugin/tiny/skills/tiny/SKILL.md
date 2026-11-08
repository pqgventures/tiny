---
name: tiny
description: Make a Tiny of any place - a pixel-art isometric diorama of a street, neighbourhood, campus or landmark, drawn from OpenStreetMap and painted tile by tile with the built-in image generation (the user's ChatGPT plan, no API key). Use when the user asks for a Tiny, a tiny city, a pixel-art or isometric map of a real place, or "@Tiny".
---

# Tiny

You turn any real place into a Tiny: one isometric pixel-art map the user can pan and zoom, made of square tiles you paint one by one.

The scripts live next to this file in `../../scripts/` (resolve the absolute path from this SKILL.md). They need `python3` with Pillow and numpy; if missing, install them for the user with `python3 -m pip install --user pillow numpy`.

## 1. Draw the base

Pick a short folder name for the place under `~/Tiny/` (e.g. `~/Tiny/largo-da-batata`). Radius: 260 m by default (15 tiles, ~9 minutes two at a time); 180 m for a single street corner (10 tiles to paint); up to 400 m if the user asks for something bigger. The base always adds a 100 m margin around the radius where the city keeps going and then fades into fog and clouds, so the Tiny never ends on an empty edge.

```
python3 <scripts>/base.py "<place, city>" <radius_m> ~/Tiny/<name>
```

It geocodes the place, downloads (for the radius plus the margin) buildings, streets, parks, water and trees from OpenStreetMap (can take up to a minute), and writes `base.png`, `tiles/<id>.png` and `plan.json` (tiles sorted from the centre outwards). Tell the user in one line what was found: the place name and number of buildings and tiles. If it says the OpenStreetMap servers are busy, tell the user in one line and run the same command again (it caches nothing until it succeeds); give up only after three tries. Then build the viewer right away and open it beside the chat, so they watch the map fill in:

```
python3 <scripts>/stitch.py ~/Tiny/<name>
```

Open `~/Tiny/<name>/index.html` (in-app browser or the user's browser).

## 2. Paint every tile

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

Run `stitch.py` a last time. `qa.json` has `corr_base` per tile (how well it kept the real geometry); repaint once any tile under 0.25. Show the user `tiny.png` and the viewer, with the number of tiles and how long it took. That is their Tiny; it stays on their computer.

