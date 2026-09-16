#!/usr/bin/env bash
# The ONE way to deploy the Hebrew tutor backend on this box:
#   gate (prompts + import smoke) -> restart web + worker -> health check.
# Refuses to restart if the gate fails. Usage: bash tools/deploy_tutor.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "== 1/3 prompt + import gate"
if ! APP_ENV=prod backend/.venv/bin/python tools/prompt_gate.py --all; then
  echo "DEPLOY ABORTED: gate failed (nothing was restarted)"; exit 1
fi
echo "== 1b/3 live prompt check (only when a prompt or a voice/image prompt in main.py changed since the last deploy)"
MARK=/var/log/iakids/prompts.deployed.sha256
CUR="$( { cat backend-ai-tutor-he/prompts/*.txt; grep -A8 '^TTS_STYLE_PREFIX = os.getenv' backend-ai-tutor-he/main.py; grep -B2 -A6 'ABSOLUTELY NO WRITTEN TEXT IN THE IMAGE' backend-ai-tutor-he/main.py; } | sha256sum | cut -c1-16 )"
PREV="$(cat "$MARK" 2>/dev/null || echo none)"
if [ "$CUR" != "$PREV" ] && [ "${SKIP_LIVE_CHECK:-0}" != "1" ]; then
  echo "prompts changed since last deploy ($PREV -> $CUR): running tools/prompt_live_check.py (3 configurations, ~3 min, ~\$0.15)"
  if ! (cd backend-ai-tutor-he && ../backend/.venv/bin/python tools/prompt_live_check.py); then
    echo "DEPLOY ABORTED: live prompt check failed (nothing was restarted). SKIP_LIVE_CHECK=1 to override knowingly."; exit 1
  fi
else
  echo "prompts unchanged since last deploy ($CUR): live check skipped"
fi
echo "== 2/3 restart iakids-tutor-web + iakids-tutor-worker"
systemctl restart iakids-tutor-web.service iakids-tutor-worker.service || { echo "restart failed"; exit 1; }
echo "== 3/3 health check"
ok=0
for i in $(seq 1 30); do
  sleep 2
  if [ "$(systemctl is-active iakids-tutor-web)" = "active" ] && \
     journalctl -u iakids-tutor-web --since "90 seconds ago" --no-pager | grep -q "Application startup complete" && \
     [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8011/)" = "200" ]; then ok=1; break; fi
done
w="$(systemctl is-active iakids-tutor-worker)"
if [ "$ok" = "1" ] && [ "$w" = "active" ]; then
  echo "$CUR" > "$MARK"
  echo "DEPLOY OK: web up (HTTP 200, startup complete), worker $w"
  journalctl -u iakids-tutor-web --since "90 seconds ago" --no-pager | grep -E 'Traceback|Error' | tail -3
  exit 0
fi
echo "DEPLOY FAILED: web=$(systemctl is-active iakids-tutor-web) worker=$w"
journalctl -u iakids-tutor-web --since "90 seconds ago" --no-pager | tail -15
exit 1
