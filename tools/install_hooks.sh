#!/usr/bin/env bash
# Installs the git pre-commit prompt gate (git hooks are not versioned). Idempotent.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cat > "$ROOT/.git/hooks/pre-commit" <<'HOOK'
#!/usr/bin/env bash
# prompt gate: blocks a commit that changes a prompt file and breaks a required placeholder/section
if git diff --cached --name-only | grep -qE '^backend-ai-tutor-he/(prompts/.*\.txt|main\.py)$'; then
  echo "prompt gate: prompt files staged — running tools/prompt_gate.py --staged"
  backend/.venv/bin/python tools/prompt_gate.py --staged || { echo "commit blocked by prompt gate"; exit 1; }
fi
HOOK
chmod +x "$ROOT/.git/hooks/pre-commit"
echo "installed $ROOT/.git/hooks/pre-commit"
