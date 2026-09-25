#!/usr/bin/env bash
# Stop whatever listens on the performance ports (fake DB, fake models, tutor copy). Never :8011 (production).
PORT=${1:-8799}
for p in $((PORT-8)) $((PORT-7)) $PORT; do
  [ "$p" = 8011 ] && continue
  for pid in $(ss -ltnpH "sport = :$p" | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do kill "$pid" 2>/dev/null; done
done
sleep 1; ss -ltnH | grep -E ":($((PORT-8))|$((PORT-7))|$PORT) " || echo "performance ports free"
