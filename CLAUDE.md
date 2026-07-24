# Journee Girls Club — Members Site

A static, no-backend member directory for the online community **Journee Girls Club**.
It is a single page ("The Journee Girls") that lists members as cards: photo on the
left, and name, title, short bio, optional Human Design pill, and up to 6 links on
the right. It is hosted directly on GitHub Pages at **members.journeegirlsclub.com**
(see `CNAME`).

## How the workflow works (READ THIS BEFORE REBUILDING)

This site uses **static site generation**. The published `index.html` is a fully
interpolated, crawlable HTML file (important for SEO) — there is **no client-side
JavaScript and no runtime data fetching of any kind**. Everything is baked in at
build time by `build.py`.

The **source of truth for member content is now the Notion database** called
**"The Journee Girls"** (`https://www.notion.so/39e0c7bdf7be8018b799dbfea6f487fa?v=39e0c7bd-f7be-800d-b963-000cb67d8519`).
`members.csv` is a generated intermediate file, produced by syncing from Notion.

**When the user asks to rebuild, update, add, remove, or edit members:**

1. Query the Notion members database view with the Notion MCP
   (`notion-query-database-view` on the database's view URL) and save the raw
   JSON rows to a file, e.g. `/tmp/notion_export.json`.
2. Run the sync script to translate that Notion export into `members.csv`:

   ```bash
   python3 sync_notion.py /tmp/notion_export.json
   # or pipe JSON directly:
   python3 sync_notion.py -
   ```

3. Run the build step to regenerate the static site:

   ```bash
   python3 build.py
   ```

That regenerates `index.html` with every member baked in as real HTML.

Do **not** hand-edit the member cards inside `index.html` — it is a generated file
and any manual edits will be overwritten on the next build. Structural/template
changes go in `build.py`; the Notion → CSV mapping lives in `sync_notion.py`;
styling goes in `styles.css`.

If the user only wants a one-off tweak that isn't in Notion yet (e.g. a quick typo
fix), it's fine to hand-edit `members.csv` directly and run `build.py` — just know
the next Notion sync will overwrite it.

## Notion ↔ CSV mapping

| Notion property | CSV column | Notes |
|---|---|---|
| `Name` | `name` | |
| `title` | `title` | |
| `bio MAX 180 CHARS` | `bio` | |
| `color` | `color` | hex code |
| `join_date` | `join_date` | Stored for reference; **not** used for site order |
| `link1_name` / `link1_url` … `link6_name` / `link6_url` | same | Up to 6 link slots. **Only shown on the site when both name and a real URL are filled** — bare `https://`, `http://`, or `#` placeholders are stripped at sync time and ignored at build time. |
| `image` | `image` | Notion stores this as an uploaded file attachment, not a filename. `sync_notion.py` extracts the original filename Notion embeds in the file reference (e.g. `elizabeth-kershaw.jpg`) and points the CSV at that file inside `images/`. **The Notion MCP cannot download the binary image itself** — if a brand-new member's photo isn't already in `images/` under that exact filename, add it manually before running `build.py`, or the site will show a broken image. |
| `HD Type` | `hd_profile` + `hd_type` | Notion multi-select (e.g. `Generator`, `3/`, `5`). `sync_notion.py` parses into profile + type. Rendered as **`3/5 Generator`** (numbers first). Hidden when blank. |

## Files

| File | Purpose |
|------|---------|
| `sync_notion.py` | Translates a Notion JSON export into `members.csv`. Run this first. |
| `members.csv` | Generated intermediate file (was previously hand-edited; now produced by `sync_notion.py`). |
| `build.py` | Offline build step. Reads `members.csv`, writes `index.html`. |
| `index.html` | **Generated** static page. Do not hand-edit the cards. |
| `styles.css` | All styling (fonts, card layout, colors). |
| `images/` | Member photos referenced by filename. Must contain a file matching each CSV `image` value. |
| `CNAME` | Custom domain for GitHub Pages: `members.journeegirlsclub.com`. |
| `.nojekyll` | Tells GitHub Pages to serve files as-is. |

## CSV format (produced by sync_notion.py)

Header row, in this order:

```
name, title, bio, image, color, join_date, hd_profile, hd_type,
link1_name, link1_url, ... link6_name, link6_url
```

- **hd_profile / hd_type** — optional Human Design fields (e.g. `4/6` and
  `Projector`). Shown as a tag pinned to the **top-right of the member photo**:
  **`4/6 Projector`** (numbers first). Leave blank in Notion to hide.

### Human Design tag (locked visual — `.member-hd` in `styles.css`)

Do not change without explicit user approval:

- **Placement:** top-right of `.member-photo-wrap`
- **Shape:** rounded square (`border-radius: 8px`), not a full pill
- **Background:** each member's `--title-color` at **60% opacity**
- **Text:** white-ish (`color-mix` ~92% white), **`font-weight: 700`**
- **Format:** `{profile} {type}` e.g. `3/5 Generator`, `4/6 Projector`

Each card sets `--title-color` in `build.py` (derived from the member's `color` hex).
- **join_date** — stored for reference only. **Member order on the site follows
  the Notion view** (manual drag order or whatever sort the view uses). Re-sync
  + rebuild after reordering in Notion.
- **linkN_name / linkN_url** — up to **6** links per member (wrap to a second
  row). A link appears on the site only when **both** the label and a real URL
  are present. Notion's empty URL placeholder (`https://` with nothing after it)
  counts as blank and is hidden.

## Local preview

```bash
python3 -m http.server
```

Then open the shown URL.

## Publishing

This site lives in its own GitHub repo (separate from the Four Languages root system).

1. Push `main` to GitHub and enable **Pages** → deploy from branch `main`, folder `/ (root)`.
2. In repo **Settings → Pages**, set custom domain to `members.journeegirlsclub.com` and enable HTTPS when ready.
3. DNS: CNAME record `members` → `elizabethkershaw.github.io`.

The `CNAME` file in this repo must match the custom domain above.
