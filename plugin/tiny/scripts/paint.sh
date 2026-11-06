#!/bin/bash
# paint.sh <tiny_folder> [parallel] — paints missing tiles with codex exec and restitches after each one
D=$(cd "$1" && pwd); P=${2:-2}; S=$(cd "$(dirname "$0")" && pwd); cd "$D"; mkdir -p gen logs
[ -s prompt.txt ] || cp "$S/prompt.txt" prompt.txt
CH=${CODEX_HOME:-$HOME/.codex}
ids=$(python3 -c "import json;print(' '.join(t['id'] for t in json.load(open('plan.json'))['tiles']))")
one() { t=$1; [ -s gen/$t.png ] && return; s=$(date +%s)
  codex exec --skip-git-repo-check -s read-only "Call your built-in image generation tool exactly ONCE, as an EDIT of exactly one input image: tiles/$t.png. The prompt is exactly the content of prompt.txt (read it and pass it verbatim). Do not copy, move, open or describe the result. Reply only: done." < /dev/null > logs/$t.log 2>&1
  sid=$(sed -n 's/^session id: //p' logs/$t.log | head -1)
  img=$(ls -t "$CH/generated_images/$sid"/*.png 2>/dev/null | head -1)
  [ -n "$img" ] && cp "$img" gen/$t.png
  echo "$t secs=$(( $(date +%s) - s )) ok=$([ -s gen/$t.png ] && echo 1 || echo 0)" >> logs/times.txt
  python3 "$S/stitch.py" "$D" > /dev/null 2>&1; }
export -f one; export D S CH
for t in $ids; do echo $t; done | xargs -P $P -I{} bash -c 'one {}'
python3 "$S/stitch.py" "$D"

