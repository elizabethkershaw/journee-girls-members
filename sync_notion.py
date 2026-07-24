#!/usr/bin/env python3
"""Sync members.csv from a Notion database export.

Notion has no code-execution / MCP access on its own, so this script does NOT
call the Notion API directly. Instead, the workflow is:

1. An agent (Claude, in Cursor) with the Notion MCP connected queries the
   members database view and writes the raw JSON rows to a file
   (e.g. /tmp/notion_export.json) using notion-query-database-view.
2. Run this script against that JSON file to translate it into members.csv:

       python3 sync_notion.py /tmp/notion_export.json

3. Run the existing static-site build step as usual:

       python3 build.py

Notion property -> CSV column mapping:
    Name                  -> name
    title                 -> title
    "bio MAX 180 CHARS"   -> bio
    color                 -> color
    date:join_date:start  -> join_date (stored only; not used for site order)
    link1_name/url .. link6_name/url -> link1..6
    image                 -> image (filename only; see below)
    HD Type               -> hd_profile + hd_type (multi-select; see parse_hd_type)

Image handling: Notion stores the "image" property as an uploaded file
attachment, not a plain filename. The Notion MCP cannot download these
binary attachments directly (notion-download-attachment only handles small
text attachments the MCP itself created). Instead, this script extracts the
original filename that Notion embeds in the file reference (e.g.
"elizabeth-kershaw.jpg") and points the CSV at that filename inside
images/. This works because photos were already placed in images/ using
matching filenames. If a brand-new member's photo filename doesn't already
exist in images/, add the file manually (same filename Notion shows) before
running build.py.
"""

import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "members.csv"
IMAGES_DIR = HERE / "images"

FIELDNAMES = [
    "name", "title", "bio", "image", "color", "join_date",
    "hd_profile", "hd_type",
    "link1_name", "link1_url", "link2_name", "link2_url",
    "link3_name", "link3_url", "link4_name", "link4_url",
    "link5_name", "link5_url", "link6_name", "link6_url",
]

HD_TYPES = (
    "Manifesting Generator",
    "Generator",
    "Manifestor",
    "Projector",
    "Reflector",
)


def parse_hd_type(raw):
    """Split Notion's HD Type multi-select into profile + type."""
    if not raw:
        return "", ""
    try:
        tags = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return "", ""
    if not tags:
        return "", ""

    hd_type = ""
    profile = ""
    profile_parts = []

    for tag in tags:
        text = (tag or "").strip()
        if not text:
            continue
        lowered = text.lower()
        matched = next((t for t in HD_TYPES if lowered == t.lower()), None)
        if matched:
            hd_type = matched
            continue
        if re.fullmatch(r"\d+/\d+", text):
            profile = text
            continue
        if re.fullmatch(r"\d+/?", text):
            profile_parts.append(text.rstrip("/"))
            continue

    if not profile:
        if len(profile_parts) >= 2:
            profile = f"{profile_parts[0]}/{profile_parts[1]}"
        elif len(profile_parts) == 1:
            profile = profile_parts[0]

    return profile, hd_type


def extract_image_filename(raw):
    """Pull the original filename out of Notion's encoded file reference."""
    if not raw:
        return ""
    try:
        refs = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return ""
    if not refs:
        return ""
    ref = refs[0]
    encoded = ref[len("file://"):] if ref.startswith("file://") else ref
    try:
        decoded = json.loads(urllib.parse.unquote(encoded))
        source = decoded.get("source", "")
    except (ValueError, TypeError):
        source = ""
    match = re.search(r"attachment:[0-9a-f-]+:(.+)$", source)
    return match.group(1) if match else ""


def normalize_url(url):
    """Return a usable https URL, or empty if placeholder / invalid."""
    url = (url or "").strip()
    if not url or url.lower() in ("#", "https://", "http://"):
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url.lstrip("/")
    return url


def clean_link_fields(out):
    """Drop link pairs unless both name and a real URL are present."""
    for i in range(1, 7):
        name = (out.get(f"link{i}_name") or "").strip()
        url = normalize_url(out.get(f"link{i}_url"))
        if not (name and url):
            out[f"link{i}_name"] = ""
            out[f"link{i}_url"] = ""
        else:
            out[f"link{i}_name"] = name
            out[f"link{i}_url"] = url


def notion_row_to_csv_row(row):
    out = {k: "" for k in FIELDNAMES}
    out["name"] = (row.get("Name") or "").strip()
    out["title"] = (row.get("title") or "").strip()
    out["bio"] = (row.get("bio MAX 180 CHARS") or "").strip()
    out["color"] = (row.get("color") or "").strip()
    out["join_date"] = (row.get("date:join_date:start") or "").strip()
    out["image"] = extract_image_filename(row.get("image"))

    for i in range(1, 7):
        out[f"link{i}_name"] = (row.get(f"link{i}_name") or "").strip()
        out[f"link{i}_url"] = (row.get(f"link{i}_url") or "").strip()

    profile, hd_type = parse_hd_type(row.get("HD Type"))
    out["hd_profile"] = profile
    out["hd_type"] = hd_type

    clean_link_fields(out)
    return out


def sync(export_path):
    with open(export_path, encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and "results" in payload:
        notion_rows = payload["results"]
    else:
        notion_rows = payload

    # Preserve Notion view row order (manual drag or view sort).
    csv_rows = [notion_row_to_csv_row(r) for r in notion_rows if (r.get("Name") or "").strip()]

    missing_images = [
        r["name"] for r in csv_rows
        if r["image"] and not (IMAGES_DIR / r["image"]).exists()
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Synced {len(csv_rows)} member(s) from Notion into {CSV_PATH}")
    if missing_images:
        print("WARNING: these members reference images not found in images/:")
        for name in missing_images:
            print(f"  - {name}")
    print("Now run: python3 build.py")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 sync_notion.py <notion_export.json>")
        print("       python3 sync_notion.py -   # read JSON from stdin")
        sys.exit(1)
    if sys.argv[1] == "-":
        payload = json.load(sys.stdin)
        export_path = HERE / ".notion_export.json"
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        sync(export_path)
    else:
        sync(sys.argv[1])
