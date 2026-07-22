#!/bin/bash
cd "$(dirname "$0")"

files=()
for f in content/*; do
  name="$(basename "$f")"
  [[ "$name" == .* ]] && continue
  lower="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *.jpg|*.jpeg|*.png|*.webp|*.gif|*.avif|*.mp4|*.webm|*.mov) files+=("$name") ;;
  esac
done

IFS=$'\n' sorted=($(sort <<<"${files[*]}")); unset IFS

json="["
for i in "${!sorted[@]}"; do
  [[ $i -gt 0 ]] && json+=","
  json+="\"${sorted[$i]}\""
done
json+="]"

echo "window.PORTFOLIO_FILES = $json;" > content/manifest.js
echo "✓ manifest.js updated with ${#sorted[@]} file(s)."
echo "You can close this window."
