#!/bin/bash
cd "$(dirname "$0")"

is_media() {
  local lower
  lower="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *.jpg|*.jpeg|*.png|*.webp|*.gif|*.avif|*.mp4|*.webm|*.mov) return 0 ;;
  esac
  return 1
}

# JSON array of sorted media file names in a directory
media_json() {
  local files=() f name
  for f in "$1"/*; do
    name="$(basename "$f")"
    [[ "$name" == .* ]] && continue
    is_media "$name" && files+=("$name")
  done
  local json="[" i=0
  if [[ ${#files[@]} -gt 0 ]]; then
    while IFS= read -r name; do
      [[ $i -gt 0 ]] && json+=","
      json+="\"$name\""
      i=$((i+1))
    done < <(printf '%s\n' "${files[@]}" | sort -V)
  fi
  json+="]"
  echo "$json"
}

# Portfolio
portfolio="$(media_json content)"
echo "window.PORTFOLIO_FILES = $portfolio;" > content/manifest.js
echo "✓ content/manifest.js updated."

# Branding: one entry per folder in branding/
mkdir -p branding
brands="{"
first=1
for d in branding/*/; do
  [[ -d "$d" ]] || continue
  brand="$(basename "$d")"
  [[ $first -eq 0 ]] && brands+=","
  brands+="\"$brand\":$(media_json "${d%/}")"
  first=0
done
brands+="}"
echo "window.BRANDING = $brands;" > branding/manifest.js
echo "✓ branding/manifest.js updated."
echo "You can close this window."
