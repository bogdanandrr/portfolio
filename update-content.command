#!/bin/bash
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Needs: brew install ffmpeg webp
HAVE_FF=0; command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && HAVE_FF=1
HAVE_WEBP=0; command -v cwebp >/dev/null && HAVE_WEBP=1
ORIGINALS="../Website-originals"   # converted originals are moved here (not deployed)

is_media() {
  local lower
  lower="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *.jpg|*.jpeg|*.png|*.webp|*.gif|*.avif|*.mp4|*.webm|*.mov) return 0 ;;
  esac
  return 1
}

# Convert new PNG/JPG images to WebP (much smaller); the original is moved to ../Website-originals
compress_images() {
  [[ $HAVE_WEBP -eq 1 ]] || return 0
  local f out
  while IFS= read -r -d '' f; do
    out="${f%.*}.webp"
    if cwebp -quiet -q 80 -m 6 "$f" -o "$out"; then
      mkdir -p "$ORIGINALS/$(dirname "$f")"
      mv "$f" "$ORIGINALS/$f"
      echo "✓ compressed $f -> $(basename "$out")"
    fi
  done < <(find "$1" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -print0)
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

# JSON object {"file": {"w": W, "h": H}} for the media files in a directory.
# The pages use it to reserve space and lazy-load without the layout jumping.
meta_json() {
  [[ $HAVE_FF -eq 1 ]] || { echo "{}"; return; }
  local f name dims json="{" first=1
  for f in "$1"/*; do
    name="$(basename "$f")"
    [[ "$name" == .* ]] && continue
    is_media "$name" || continue
    dims="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$f" 2>/dev/null | head -1)"
    [[ "$dims" == *,* ]] || continue
    [[ $first -eq 0 ]] && json+=","
    json+="\"$name\":{\"w\":${dims%,*},\"h\":${dims#*,}}"
    first=0
  done
  json+="}"
  echo "$json"
}

# Poster frame for every video in content/
make_posters() {
  [[ $HAVE_FF -eq 1 ]] || { echo "! ffmpeg not found: skipping posters (brew install ffmpeg)"; return; }
  mkdir -p content/posters
  local f name poster
  for f in content/*; do
    name="$(basename "$f")"
    echo "$name" | grep -qiE '\.(mp4|webm|mov)$' || continue
    poster="content/posters/${name%.*}.jpg"
    if [[ ! -f "$poster" || "$f" -nt "$poster" ]]; then
      ffmpeg -v error -y -ss 1 -i "$f" -frames:v 1 -vf "scale='min(640,iw)':-2" -q:v 4 "$poster" </dev/null \
        || ffmpeg -v error -y -i "$f" -frames:v 1 -vf "scale='min(640,iw)':-2" -q:v 4 "$poster" </dev/null
      echo "✓ poster for $name"
    fi
  done
}

# Portfolio
compress_images content
make_posters
portfolio="$(media_json content)"
echo "window.PORTFOLIO_FILES = $portfolio;" > content/manifest.js
echo "window.PORTFOLIO_META = $(meta_json content);" >> content/manifest.js
echo "✓ content/manifest.js updated."

# Branding: one entry per folder in branding/
mkdir -p branding
compress_images branding
brands="{"
metas="{"
first=1
for d in branding/*/; do
  [[ -d "$d" ]] || continue
  brand="$(basename "$d")"
  [[ $first -eq 0 ]] && { brands+=","; metas+=","; }
  brands+="\"$brand\":$(media_json "${d%/}")"
  metas+="\"$brand\":$(meta_json "${d%/}")"
  first=0
done
brands+="}"
metas+="}"
echo "window.BRANDING = $brands;" > branding/manifest.js
echo "window.BRANDING_META = $metas;" >> branding/manifest.js
echo "✓ branding/manifest.js updated."
echo "You can close this window."
