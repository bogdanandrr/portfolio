#!/usr/bin/env python3
"""
Builds the portfolio from the projects/ folder.

projects/
  01 Tom Ford Concept Campaign/     <- "01 " sets the order, the rest is the title
    poster.mp4 | poster.png ...     <- shown on the homepage and first on the project page
    real-poster.mp4 (optional)      <- if present, shown on the homepage instead of the poster
    descriere.txt                   <- optional description (blank line = new paragraph)
    1.png, 2.png, clip.mp4 ...      <- the rest of the project page, in filename order

What it does (safe to run again and again):
  1. Compresses every new image (-> .webp, long edge max 2560px) and video (-> H.264 .mp4,
     long edge max 1920px, audio kept). Originals are MOVED to ../Website-originals/projects/.
  2. Makes a still frame for every video in assets/thumbs/<slug>/ (shown while the video loads).
  3. Writes one page per project: <slug>.html (e.g. tom-ford-concept-campaign.html).
  4. Rewrites the project list on the homepage (between the PROJECTS markers in index.html).

Needs ffmpeg, ffprobe and cwebp (brew install ffmpeg webp).
"""

import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent      # the site folder (this file is in scripts/)
PROJECTS = ROOT / "projects"
THUMBS = ROOT / "assets" / "thumbs"
ORIGINALS = ROOT.parent / "Website-originals" / "projects"
INDEX = ROOT / "index.html"

IMAGE_IN = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".bmp"}
IMAGE_OK = {".webp", ".gif", ".avif"}
VIDEO = {".mp4", ".mov", ".m4v", ".webm"}

IMG_MAX = 2560          # long edge, px
IMG_QUALITY = 82
VID_MAX = 1920          # long edge, px
VID_CRF = 24
DONE_TAG = "andreibogdan-web"   # written into compressed videos so they are never compressed twice

RESERVED = {"index", "contact", "brand", "branding", "style", "build-projects"}
GENERATOR = '<meta name="generator" content="build-projects.py" />'
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

for tool in ("ffmpeg", "ffprobe", "cwebp"):
    if not shutil.which(tool):
        sys.exit(f"! {tool} not found. Install it with: brew install ffmpeg webp")


def log(msg):
    print(msg, flush=True)


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def url(path):
    """Relative URL for a file under the site root (spaces, # etc. encoded)."""
    return quote(path.relative_to(ROOT).as_posix(), safe="/")


def esc(s):
    return html.escape(s, quote=True)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height:stream_tags=rotate:format=duration:format_tags=comment",
         "-of", "json", str(path)],
        capture_output=True, text=True).stdout
    data = json.loads(out or "{}")
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    w, h = v.get("width", 0), v.get("height", 0)
    if str(v.get("tags", {}).get("rotate", "0")) in ("90", "-90", "270"):
        w, h = h, w
    fmt = data.get("format", {})
    return {
        "w": w, "h": h,
        "audio": any(s.get("codec_type") == "audio" for s in streams),
        "duration": float(fmt.get("duration", 0) or 0),
        "comment": fmt.get("tags", {}).get("comment", ""),
    }


def move_original(src, folder_name):
    dest_dir = ORIGINALS / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():                     # never overwrite an older original
        stem, n = dest.stem, 2
        while (dest_dir / f"{stem}-{n}{dest.suffix}").exists():
            n += 1
        dest = dest_dir / f"{stem}-{n}{dest.suffix}"
    shutil.move(str(src), str(dest))


def compress_image(src, folder_name):
    out = src.with_suffix(".webp")
    info = probe(src)
    resize = []
    if max(info["w"], info["h"]) > IMG_MAX:
        resize = ["-resize", str(IMG_MAX), "0"] if info["w"] >= info["h"] else ["-resize", "0", str(IMG_MAX)]
    tmp = out.with_name(out.stem + ".tmp.webp")
    r = subprocess.run(["cwebp", "-quiet", "-q", str(IMG_QUALITY), "-m", "6", "-sharp_yuv",
                        "-metadata", "none", *resize, str(src), "-o", str(tmp)])
    if r.returncode != 0:
        log(f"  ! could not convert {src.name}")
        tmp.unlink(missing_ok=True)
        return
    before = src.stat().st_size
    tmp.replace(out)
    move_original(src, folder_name)
    log(f"  ✓ {src.name} -> {out.name}  ({before / 1e6:.1f} MB -> {out.stat().st_size / 1e6:.2f} MB)")


def compress_video(src, folder_name):
    info = probe(src)
    if info["comment"] == DONE_TAG:
        return
    out = src.with_suffix(".mp4")
    tmp = src.with_name(src.stem + ".tmp.mp4")
    if info["w"] >= info["h"]:
        scale = f"scale='min({VID_MAX},iw)':-2"
    else:
        scale = f"scale=-2:'min({VID_MAX},ih)'"
    audio = ["-c:a", "aac", "-b:a", "128k"] if info["audio"] else ["-an"]
    log(f"  … compressing {src.name} ({src.stat().st_size / 1e6:.0f} MB, {info['duration']:.0f}s)")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                        "-map", "0:v:0", "-map", "0:a:0?", "-vf", scale,
                        "-c:v", "libx264", "-preset", "slow", "-tune", "film", "-crf", str(VID_CRF), "-maxrate", "5M", "-bufsize", "10M",
                        "-pix_fmt", "yuv420p", *audio,
                        "-movflags", "+faststart", "-metadata", f"comment={DONE_TAG}", str(tmp)],
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0 or not tmp.exists():
        log(f"  ! could not compress {src.name}")
        tmp.unlink(missing_ok=True)
        return
    before = src.stat().st_size
    if tmp.stat().st_size >= before and src.suffix.lower() == ".mp4":
        # already smaller than our encode: keep it as is, just tag it
        tmp.unlink()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0", "-c", "copy",
                        "-movflags", "+faststart", "-metadata", f"comment={DONE_TAG}", str(tmp)],
                       stdin=subprocess.DEVNULL)
        if not tmp.exists():
            log(f"  ! could not tag {src.name}, left as is")
            return
    move_original(src, folder_name)
    tmp.replace(out)
    log(f"  ✓ {src.name} -> {out.name}  ({before / 1e6:.0f} MB -> {out.stat().st_size / 1e6:.1f} MB)")


def make_still(video, slug, info):
    still = THUMBS / slug / (video.stem + ".jpg")
    if still.exists() and still.stat().st_mtime >= video.stat().st_mtime:
        return still
    still.parent.mkdir(parents=True, exist_ok=True)
    t = "1" if info["duration"] > 2 else "0"
    scale = "scale='min(1280,iw)':-2" if info["w"] >= info["h"] else "scale=-2:'min(1280,ih)'"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", t, "-i", str(video), "-frames:v", "1",
                    "-vf", scale, "-q:v", "4", str(still)], stdin=subprocess.DEVNULL)
    return still


# ---------------------------------------------------------------- HTML pieces

def media_html(item, cls, eager=False, sound=False):
    """<img> or <video> for one media item. Videos autoplay muted while on screen (site.js)."""
    w, h = item["w"], item["h"]
    style = f'style="--ar:{w}/{h}"'
    if item["kind"] == "image":
        load = 'fetchpriority="high"' if eager else 'loading="lazy"'
        return (f'<div class="{cls}" {style}><img src="{item["src"]}" width="{w}" height="{h}" '
                f'alt="" {load} decoding="async" /></div>')
    btn = ""
    if sound and item["audio"]:
        btn = ('<button class="sound-toggle" type="button" aria-label="Turn sound on" aria-pressed="false">'
               '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M11 5 6 9H2v6h4l5 4V5z"/><path class="on" d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>'
               '<path class="off" d="m23 9-6 6M17 9l6 6"/></svg></button>')
    return (f'<div class="{cls} is-video" {style}><video muted loop playsinline preload="none" '
            f'poster="{item["still"]}" width="{w}" height="{h}" data-autoplay>'
            f'<source src="{item["src"]}" type="video/mp4" /></video>{btn}</div>')


def paragraphs(text):
    return "".join(f"<p>{esc(p.strip())}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())


FOOTER = """  <footer class="site-footer">
    <a href="mailto:ciobanu.andreibogdan97@gmail.com" class="footer-mail">ciobanu.andreibogdan97@gmail.com</a>
    <div class="footer-social">
      <a href="https://www.instagram.com/bogdan.andrr/" target="_blank" rel="noopener" aria-label="Instagram">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><circle cx="12" cy="12" r="4.5"/><circle cx="17.5" cy="6.5" r="0.8" fill="currentColor" stroke="none"/></svg>
      </a>
      <a href="https://www.linkedin.com/in/andreibogdanciobanu/" target="_blank" rel="noopener" aria-label="LinkedIn">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>
      </a>
    </div>
  </footer>"""


def project_page(p, nxt, css_v):
    desc = paragraphs(p["description"])
    gallery = "\n      ".join(media_html(m, "g-item", sound=True) for m in p["rest"])
    meta_desc = esc(re.sub(r"\s+", " ", p["description"]).strip()[:160] or f"{p['title']}, a project by Andrei Bogdan.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  {GENERATOR}
  <title>{esc(p["title"])} — Andrei Bogdan</title>
  <meta name="description" content="{meta_desc}" />
  <link rel="preload" href="assets/fonts/Switzer-Medium.woff2" as="font" type="font/woff2" crossorigin />
  <link rel="stylesheet" href="assets/style.css?v={css_v}" />
</head>
<body class="project-page">
  <!-- Generated by scripts/build-projects.py from "projects/{esc(p["folder"])}". Edits here are overwritten. -->
  <header>
    <a href="index.html" class="logo">AndreiBogdan</a>
    <nav class="nav-links">
      <a href="contact.html">CONTACT</a>
    </nav>
  </header>

  <main class="pp">
    <div class="pp-head">
      <a class="pp-back" href="index.html#projects">← All projects</a>
      <h1 class="pp-title">{esc(p["title"])}</h1>
      {f'<div class="pp-desc">{desc}</div>' if desc else ''}
    </div>

    {media_html(p["poster"], "pp-poster", eager=True, sound=True)}

    {f'<div class="gallery">{chr(10)}      {gallery}{chr(10)}    </div>' if p["rest"] else ''}

    <a class="pp-next" href="{nxt["slug"]}.html">
      <span>Next project</span>
      <strong>{esc(nxt["title"])}</strong>
    </a>
  </main>

{FOOTER}

  <script src="assets/site.js?v={css_v}"></script>
</body>
</html>
"""


def homepage_list(projects):
    rows = []
    for i, p in enumerate(projects, 1):
        desc = paragraphs(p["description"])
        home = p["home"]
        media = media_html(home, "project-media", eager=False)
        # Portrait posters leave a lot of empty space on wide screens: add the project's first
        # two images next to them as a small staggered collage.
        extras = [it for it in p["rest"] if it["kind"] == "image"][:2] if home["h"] > home["w"] else []
        if extras:
            tiles = "".join(f'<div class="project-extra"><img src="{it["src"]}" alt="" loading="lazy" decoding="async" /></div>'
                            for it in extras)
            media = f'<div class="project-group">{media}<div class="project-extras">{tiles}</div></div>'
        rows.append(f"""      <a class="project" href="{p["slug"]}.html">
        {media}
        <div class="project-text">
          <span class="project-num">{i:02d}</span>
          <h2 class="project-title">{esc(p["title"])}</h2>
          {f'<div class="project-desc">{desc}</div>' if desc else ''}
          <span class="project-more">View project</span>
        </div>
      </a>""")
    return "\n".join(rows)


# ---------------------------------------------------------------- main

def main():
    if not PROJECTS.is_dir():
        sys.exit("! projects/ folder not found")

    folders = sorted((d for d in PROJECTS.iterdir() if d.is_dir() and not d.name.startswith(".")),
                     key=lambda d: natural_key(d.name))
    projects, slugs = [], set()

    for d in folders:
        m = re.match(r"^\s*\d+[\s._-]*(.+)$", d.name)
        title = (m.group(1) if m else d.name).strip()
        slug = slugify(title) or "project"
        if slug in RESERVED:
            slug = "project-" + slug
        base, n = slug, 2
        while slug in slugs:
            slug, n = f"{base}-{n}", n + 1
        slugs.add(slug)
        log(f"\n{d.name}  ->  {slug}.html")

        # 1. compress
        for f in sorted(d.iterdir(), key=lambda f: natural_key(f.name)):
            if f.name.startswith(".") or not f.is_file() or ".tmp." in f.name:
                continue
            ext = f.suffix.lower()
            if ext in IMAGE_IN:
                compress_image(f, d.name)
            elif ext in VIDEO:
                compress_video(f, d.name)

        # 2. collect media
        items = []
        for f in sorted(d.iterdir(), key=lambda f: natural_key(f.name)):
            ext = f.suffix.lower()
            if f.name.startswith(".") or not f.is_file() or ".tmp." in f.name:
                continue
            if ext not in IMAGE_OK and ext not in VIDEO:
                continue
            info = probe(f)
            if not info["w"]:
                log(f"  ! skipped {f.name} (could not read it)")
                continue
            item = {"name": f.name, "src": url(f), "w": info["w"], "h": info["h"],
                    "kind": "video" if ext in VIDEO else "image", "audio": info["audio"]}
            if item["kind"] == "video":
                item["still"] = url(make_still(f, slug, info))
            items.append(item)
        if not items:
            log("  ! no images or videos, project skipped")
            continue

        # Remove video stills that no longer belong to a video (renamed / deleted files)
        keep = {Path(it["name"]).stem + ".jpg" for it in items if it["kind"] == "video"}
        for still in (THUMBS / slug).glob("*.jpg") if (THUMBS / slug).exists() else []:
            if still.name not in keep:
                still.unlink()

        def named(stem):
            return next((it for it in items if Path(it["name"]).stem.lower() == stem), None)

        poster = named("poster")
        if not poster:
            videos = [it for it in items if it["kind"] == "video"]
            poster = videos[0] if len(videos) == 1 else items[0]
            log(f"  (no file named 'poster': using {poster['name']})")
        # Optional "real-poster": shown on the homepage instead of the poster (and not in the gallery)
        home = named("real-poster")
        if home is poster:
            home = None
        if home:
            log(f"  homepage uses {home['name']}, project page starts with {poster['name']}")

        desc_file = next((f for f in d.iterdir() if f.name.lower() in ("descriere.txt", "description.txt")), None)
        description = desc_file.read_text(encoding="utf-8", errors="ignore").strip() if desc_file else ""

        projects.append({"folder": d.name, "title": title, "slug": slug, "description": description,
                         "poster": poster, "home": home or poster,
                         "rest": [it for it in items if it is not poster and it is not home]})

    css_v = str(int(max((ROOT / "assets" / f).stat().st_mtime for f in ("style.css", "site.js"))))

    # 3. project pages (and remove pages of projects that no longer exist)
    current = {p["slug"] + ".html" for p in projects}
    for f in ROOT.glob("*.html"):
        if f.name not in current and GENERATOR in f.read_text(encoding="utf-8", errors="ignore"):
            f.unlink()
            log(f"\n✗ removed old page {f.name}")
    for i, p in enumerate(projects):
        nxt = projects[(i + 1) % len(projects)]
        (ROOT / f"{p['slug']}.html").write_text(project_page(p, nxt, css_v), encoding="utf-8")
    for d in THUMBS.glob("*") if THUMBS.exists() else []:
        if d.is_dir() and d.name not in slugs:
            shutil.rmtree(d)

    # 4. homepage list
    page = INDEX.read_text(encoding="utf-8")
    if START in page and END in page:
        a, b = page.index(START) + len(START), page.index(END)
        page = page[:a] + "\n" + homepage_list(projects) + "\n      " + page[b:]
        page = re.sub(r'(style\.css|site\.js)\?v=\d+', lambda m: f"{m.group(1)}?v={css_v}", page)
        INDEX.write_text(page, encoding="utf-8")
        log(f"\n✓ homepage updated with {len(projects)} projects")
    else:
        log("\n! index.html has no PROJECTS markers: homepage not updated")

    log(f"✓ {len(projects)} project pages written. Originals are in {ORIGINALS}")


if __name__ == "__main__":
    main()
