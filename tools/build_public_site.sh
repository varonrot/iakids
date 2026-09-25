#!/usr/bin/env bash
# Render publishes only the browser-facing files copied into this directory.
set -euo pipefail

out=public-site
rm -rf "$out"
mkdir -p "$out"

# Every directory here contains pages or assets intended for visitors. Do not
# include server code, internal documents, migrations, prompts, or tooling.
public_dirs=(
  actividades-educativas admin ar assets blog contact coppa da de eng es fi fr
  frontend-v2 games guia-para-padres he he2 id it ja ko nl no onboarding
  padres parent-dashboard pl planes privacy pt refunds ro support support-dashboard
  sv terms tr workspace
)

for file in index.html favicon.ico robots.txt sitemap.xml askie-space-bg.jpg explain-topic.png smart-riddle.png; do
  if [[ -f "$file" ]]; then cp "$file" "$out/$file"; fi
done

for dir in "${public_dirs[@]}"; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r -d '' file; do
    case "/$file" in
      */tools/*|*/prompts/*|*/data/*|*/tests/*|*/test/*|*/__pycache__/*|*/node_modules/*) continue ;;
    esac
    name=${file##*/}
    case "$name" in
      .*|*back_up*|*backup*|*BACKUP*|*old*|*.map) continue ;;
      *.html|*.htm|*.css|*.js|*.svg|*.png|*.jpg|*.jpeg|*.gif|*.webp|*.avif|*.ico|*.woff|*.woff2|*.ttf|*.otf|*.eot|*.mp3|*.mp4|*.webm|*.ogg|*.wav|*.pdf|*.webmanifest) ;;
      *) continue ;;
    esac
    mkdir -p "$out/$(dirname "$file")"
    cp "$file" "$out/$file"
  done < <(find "$dir" -type f -print0)
done

test -f "$out/index.html"
test -f "$out/eng/index.html"
test ! -e "$out/docs/BUGFIXES.md"
test ! -e "$out/backend/main.py"
printf 'Built public site: %s files\n' "$(find "$out" -type f | wc -l)"
