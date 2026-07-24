# The Journee Girls — members directory

Static member directory for [Journee Girls Club](https://journeegirlsclub.com).

**Live site:** `https://members.journeegirlsclub.com` (GitHub Pages)

## Update workflow

1. Export rows from Notion database **The Journee Girls** (via Notion MCP or manual JSON export).
2. Sync to CSV:

   ```bash
   python3 sync_notion.py .notion_export.json
   ```

3. Rebuild HTML:

   ```bash
   python3 build.py
   ```

4. Commit and push — GitHub Pages redeploys automatically.

## Local preview

```bash
python3 -m http.server
```

Open the URL shown in the terminal.

## Files

| File | Role |
|------|------|
| `index.html` | Generated site (do not hand-edit cards) |
| `members.csv` | Generated from Notion |
| `build.py` / `sync_notion.py` | Build pipeline |
| `CNAME` | Custom domain for Pages |
| `.nojekyll` | Required for GitHub Pages |

See `CLAUDE.md` for full Notion ↔ CSV mapping.
