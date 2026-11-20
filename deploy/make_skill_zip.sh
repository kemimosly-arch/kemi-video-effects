#!/usr/bin/env bash
# Builds effects.zip: the version of this skill you upload to claude.ai / the Claude app
# (Customize > Skills > + > Upload a skill). The GitHub "Download ZIP" will NOT upload: its folder is
# named kemi-video-effects-main (must match the skill name "effects") and it carries ~1,000 extra files
# (the web app, deploy files and the full sound packs). This keeps only what the skill uses.
set -e
cd "$(dirname "$0")/.."
OUT=/tmp/skillzip; rm -rf "$OUT" && mkdir -p "$OUT/effects"
D="$OUT/effects"
cp SKILL.md LICENSE requirements.txt "$D/"
mkdir -p "$D/scripts" && cp scripts/*.py scripts/*.sh "$D/scripts/" 2>/dev/null || true
cp -r fonts models "$D/"
mkdir -p "$D/assets/sfx/packs"
cp assets/sfx/*.wav "$D/assets/sfx/" 2>/dev/null || true
cp assets/sfx/packs/LICENSE-CC0.txt "$D/assets/sfx/packs/"
# only the pack sounds the skill actually maps to
PYBIN=$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )
$PYBIN -I - "$D" <<'PY'
import os, sys, shutil
sys.path.insert(0, 'scripts')
import sfx
dst = sys.argv[1]; used = set()
def walk(v):
    if isinstance(v, str) and '/' in v: used.add(v)
    elif isinstance(v, (list, tuple)): [walk(x) for x in v]
    elif isinstance(v, dict): [walk(x) for x in v.values()]
for n in ('DESIGNED', 'NEW_FX_SOUNDS', 'SOUNDS'): walk(getattr(sfx, n, {}))
n = 0
for u in sorted(used):
    src = os.path.join('assets', 'sfx', 'packs', u + '.mp3')
    if os.path.exists(src):
        os.makedirs(os.path.join(dst, 'assets', 'sfx', 'packs', os.path.dirname(u)), exist_ok=True)
        shutil.copy(src, os.path.join(dst, 'assets', 'sfx', 'packs', u + '.mp3')); n += 1
print(f'  kept {n} pack sounds')
PY
find "$OUT" -name '__pycache__' -prune -exec rm -rf {} + ; find "$OUT" -name '.DS_Store' -delete
rm -f effects.zip && (cd "$OUT" && zip -qr "$OLDPWD/effects.zip" effects)
echo "Built effects.zip: $(unzip -l effects.zip | tail -1 | awk '{print $2}') files, $(du -h effects.zip | cut -f1)"
