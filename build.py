#!/usr/bin/env python3
"""Offline build step for the Journee Girls members directory.

Reads members.csv and writes a fully interpolated, static index.html so the
published page contains all member content as real HTML (good for SEO). There
is no client-side CSV fetching — everything is baked in at build time.

Usage:
    python3 build.py

Re-run this whenever members.csv changes.

CSV columns (header row required, in any order):
    name, title, bio, image, color, join_date, hd_profile, hd_type,
    link1_name, link1_url, ... up to link6_name, link6_url

- image : filename inside the /images folder (e.g. "elizabeth-kershaw.jpg")
- color : a hex code (e.g. "#9B87F5"). The card's soft background tint and the
          title colour are both derived from this single value.
- join_date : the date the member joined, as YYYY-MM-DD (e.g. "2026-01-15").
          Stored for reference only; member order comes from row order in the CSV
          (which mirrors the Notion view order after sync_notion.py).
- hd_profile / hd_type : optional Human Design fields (e.g. "2/4" and "Generator").
          Rendered as a soft tag pinned to the top-right of the member photo
          (e.g. "3/5 Generator", profile numbers first). Blank = hidden.
          Visual spec is locked in styles.css (.member-hd).
- linkN_name / linkN_url : optional, up to 6 links per member (wraps to a second row).
          Only shown when both fields are filled and the URL is real (not "#" or bare "https://").
"""

import csv
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "members.csv")
OUT_PATH = os.path.join(HERE, "index.html")
MAX_LINKS = 6
DEFAULT_HEX = "#B6ADCB"


# --------------------------------------------------------------------------- #
# Colour helpers — derive card tint + title colour from one hex               #
# --------------------------------------------------------------------------- #

def normalize_hex(value):
    if not value:
        return DEFAULT_HEX
    hexv = value.strip().lstrip("#")
    if len(hexv) == 3:
        hexv = "".join(c * 2 for c in hexv)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hexv):
        return DEFAULT_HEX
    return "#" + hexv.lower()


def hex_to_rgb(hexv):
    h = hexv.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def mix(c, target, t):
    return tuple(round(c[i] + (target[i] - c[i]) * t) for i in range(3))


def rgb_css(rgb):
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"


def card_background(hexv):
    base = hex_to_rgb(hexv)
    white = (255, 255, 255)
    light = rgb_css(mix(base, white, 0.86))
    deep = rgb_css(mix(base, white, 0.72))
    return f"linear-gradient(135deg, {light} 0%, {deep} 100%)"


def title_color(hexv):
    base = hex_to_rgb(hexv)
    dark = (43, 39, 64)
    return rgb_css(mix(base, dark, 0.5))


# --------------------------------------------------------------------------- #
# Rendering                                                                    #
# --------------------------------------------------------------------------- #

def esc(text):
    return html.escape((text or "").strip())


def esc_attr(text):
    return html.escape((text or "").strip(), quote=True)


def is_valid_link(name, url):
    """Only render links with both a label and a real destination URL."""
    if not name or not url:
        return False
    normalized = url.strip().lower()
    if normalized in ("#", "https://", "http://"):
        return False
    return True


def collect_links(row):
    links = []
    for i in range(1, MAX_LINKS + 1):
        name = (row.get(f"link{i}_name") or "").strip()
        url = (row.get(f"link{i}_url") or "").strip()
        if is_valid_link(name, url):
            links.append((name, url))
    return links


def format_human_design(row):
    """Compose '2/4 Generator' (profile numbers first, then type)."""
    profile = (row.get("hd_profile") or "").strip()
    hd_type = (row.get("hd_type") or "").strip()
    if profile and hd_type:
        return f"{profile} {hd_type}"
    return profile or hd_type


def render_card(row):
    hexv = normalize_hex(row.get("color"))
    name = esc(row.get("name"))
    title = esc(row.get("title"))
    bio = esc(row.get("bio"))
    image = (row.get("image") or "").strip()

    parts = [
        f'      <article class="member-card" style="--brand: {hexv}; --title-color: {title_color(hexv)}; background: {card_background(hexv)};">'
    ]

    alt = f"Photo of {name}" if name else "Member photo"
    src = f"images/{esc_attr(image)}" if image else ""
    hd_label = format_human_design(row)
    parts.append('        <div class="member-photo-wrap">')
    parts.append(
        f'          <img class="member-photo" src="{src}" alt="{alt}" loading="lazy" />'
    )
    if hd_label:
        parts.append(f'          <span class="member-hd">{esc(hd_label)}</span>')
    parts.append("        </div>")

    parts.append('        <div class="member-body">')
    parts.append('          <div class="member-content">')
    if name:
        parts.append(f'            <h2 class="member-name">{name}</h2>')
    if title:
        parts.append(f'            <p class="member-title">{title}</p>')
    if bio:
        parts.append(f'            <p class="member-bio">{bio}</p>')
    parts.append("          </div>")

    links = collect_links(row)
    if links:
        parts.append('          <div class="member-links">')
        for lname, lurl in links:
            parts.append(
                f'            <a class="member-link" href="{esc_attr(lurl)}" '
                f'target="_blank" rel="noopener noreferrer">'
                f'<span class="arrow">\u2197</span>{esc(lname)}</a>'
            )
        parts.append("          </div>")

    parts.append("        </div>")
    parts.append("      </article>")
    return "\n".join(parts)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The Journee Girls</title>
  <meta name="description" content="Members of Journee Girls Club — an online community of female founders and creators." />
  <meta property="og:title" content="The Journee Girls" />
  <meta property="og:description" content="Members of Journee Girls Club — an online community of female founders and creators." />
  <meta property="og:type" content="website" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Anek+Bangla:wght@500;600;700&family=Mulish:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="styles.css?v=21" />
</head>
<body>
  <!--
    This file is GENERATED by build.py from members.csv.
    Do not edit the member cards by hand — edit members.csv and re-run:
        python3 build.py
  -->
  <main class="page">
    <h1 class="page-title">The Journee Girls</h1>

    <section class="members-grid">
{cards}
    </section>
  </main>
</body>
</html>
"""


def build():
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        # Preserve CSV row order (set by sync_notion.py from the Notion view).
        rows = [r for r in csv.DictReader(f) if (r.get("name") or "").strip()]

    cards = "\n".join(render_card(r) for r in rows)
    html_out = PAGE_TEMPLATE.format(cards=cards)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Built {OUT_PATH} with {len(rows)} member(s).")


if __name__ == "__main__":
    build()
