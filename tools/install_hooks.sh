#!/usr/bin/env bash
# Installs the git pre-commit gate and runs the full automated suite once, so a fresh
# clone is verified at install time and not on the first deploy. Idempotent.
#
# 2026-09-17: added after a run of regressions that all reached production because
# nothing ran the checks automatically — the lesson layout that worked only for
# מדעים, images that froze the lesson, a corrupted API key that produced a lesson
# with no pictures, and a Learning Coach judging the child against an answer it
# invented. Every one of those now has a rule in tools/prompt_gate.py.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"

cat > "$ROOT/.git/hooks/pre-commit" <<'HOOK'
#!/usr/bin/env bash
# prompt gate: blocks a commit that breaks a prompt rule, a code rule or the lesson screen
if git diff --cached --name-only | grep -qE '^(backend-ai-tutor-he/(prompts/.*\.txt|main\.py|english_tutor\.py|request_cache\.py)|he/workspace/index\.html|tools/prompt_gate\.py|performance/(routes|static_checks)\.py|performance/results/latest-fake\.json)$'; then
  echo "prompt gate: running tools/prompt_gate.py --staged"
  backend/.venv/bin/python tools/prompt_gate.py --staged || { echo "commit blocked by prompt gate"; exit 1; }
fi
HOOK
chmod +x "$ROOT/.git/hooks/pre-commit"
echo "installed $ROOT/.git/hooks/pre-commit"

if [ "${SKIP_GATE:-0}" = "1" ]; then
  echo "SKIP_GATE=1: the full suite was not run"
  exit 0
fi

if [ ! -x "$PY" ]; then
  echo "WARNING: $PY not found — create the venv, then re-run this script to verify the checks"
  exit 0
fi

echo
echo "== running the full automated suite (tools/prompt_gate.py --all)"
if "$PY" "$ROOT/tools/prompt_gate.py" --all; then
  echo "install OK: hook installed and every check passes"
else
  echo "INSTALL FAILED: the checks above do not pass in this clone — fix them before deploying"
  exit 1
fi
