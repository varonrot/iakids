#!/usr/bin/env bash
# Snapshot main.py (both backends) + every prompt file into V<N>_BACKUP (auto-increment).
# Usage: bash .claude/skills/backup/backup.sh [optional note]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

# next version number: highest existing V<N>_BACKUP + 1
N=$(ls -d V*_BACKUP 2>/dev/null | sed -nE 's/^V([0-9]+)_BACKUP$/\1/p' | sort -n | tail -1)
N=$(( ${N:-0} + 1 ))
DEST="V${N}_BACKUP"
mkdir -p "$DEST/root" "$DEST/backend" "$DEST/backend/prompts" "$DEST/backend-ai-tutor-he" "$DEST/backend-ai-tutor-he/prompts"

cp -p backend/main.py                 "$DEST/backend/main.py"
cp -p backend-ai-tutor-he/main.py     "$DEST/backend-ai-tutor-he/main.py"
shopt -s nullglob; for f in iakids_*_prompt.txt; do cp -p "$f" "$DEST/root/"; done; shopt -u nullglob   # root copies were removed 2026-09-15
cp -p backend/prompts/*.txt           "$DEST/backend/prompts/"
cp -pR backend-ai-tutor-he/prompts/. "$DEST/backend-ai-tutor-he/prompts/"   # incl. subfolders (prompts/homework/, 2026-09-23)

# verify byte-identical copies
diff -q backend/main.py "$DEST/backend/main.py"
diff -q backend-ai-tutor-he/main.py "$DEST/backend-ai-tutor-he/main.py"
diff -rq backend/prompts "$DEST/backend/prompts"
diff -rq backend-ai-tutor-he/prompts "$DEST/backend-ai-tutor-he/prompts"
shopt -s nullglob; for f in iakids_*_prompt.txt; do diff -q "$f" "$DEST/root/$f"; done; shopt -u nullglob

COUNT=$(( $(find "$DEST" -type f | wc -l) + 1 ))   # +1 for this README
cat > "$DEST/README.md" <<MD
# ${DEST} — main.py + prompts snapshot

Created: $(date -u +'%Y-%m-%d %H:%M UTC')
Git HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo n/a)
Note: ${1:-}
Files: ${COUNT}

- \`backend/main.py\`                  — core chat API
- \`backend-ai-tutor-he/main.py\`      — Hebrew AI tutor API
- \`root/\`                            — \`iakids_*_prompt.txt\` from repo root
- \`backend/prompts/\`                 — core chat prompts
- \`backend-ai-tutor-he/prompts/\`     — Hebrew tutor prompts

Do not edit files here; restore by copying back to the original path.
MD

echo "OK: $DEST ($COUNT files, verified identical)"
