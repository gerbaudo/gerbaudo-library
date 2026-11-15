---
name: library
description: Maintain Davide's book library in this repo. Use when he asks to update the library from Screvi, add a summary for a book, add a book (by ISBN or title), import new My Library exports, push quotes to Screvi, or rebuild and publish the library page.
---

# Gerbaudo Library

The library is a static page (`docs/index.html`, served by GitHub Pages at
https://gerbaudo.github.io/gerbaudo-library) built from CSV files. Read `README.md`
for the full pipeline. Key files:

| File | What it is | Edited by |
|---|---|---|
| `data/mylibrary-<date>.csv` | My Library app snapshots (paper books, page marks) | importer |
| `data/screvi_sources_snapshot.json` | Screvi `list-sources` output: per-book highlight counts, no text | this skill |
| `data/screvi_sources.csv` | Screvi source name → proper title/author, and `kind` (book, paper, skip) | this skill, confirmed by Davide |
| `data/screvi.csv` | per-book highlight counts, from the snapshot (or a CSV export) | importer |
| `data/manual.csv` | books added by hand | `add_book.py` or by hand |
| `data/notes.csv` | `id, title, years_read, year_source, must_read, todo, summary_status, summary` (public) | by hand / this skill |
| `data/private/notes/<id>.md` | long notes, git-ignored | by hand |
| `data/notes_private.enc.json` | encrypted long notes (committed, shown behind a password) | `private_notes.py` |
| `data/overrides.csv` | `id, field, value` manual fixes that always win | by hand |
| `data/books.csv` | merged result — never edit, regenerate with `merge.py` | `merge.py` |

Rules already decided by Davide:
- Same book in two My Library scans: the newer count wins. Same title and author twice
  in one scan: keep one, with the largest count.
- Paper marks and Kindle highlights of the same book: use the larger, never the sum.
- Papers, white papers and articles stay out of the library (`kind = paper`).
- Book quotes go to Screvi, not to this repo. Summaries are public and in his own words.
  Long notes are private (encrypted). The password is not in the repo: ask Davide, or
  search his past Claude chats for "library notes password". Never write it into a file.
- Commits use the repo's git identity (GitHub no-reply address). Never put Davide's
  personal email in commits, scripts, headers or URLs.

Always finish a change with: `cd scripts && python merge.py && python build_site.py`,
check the output for warnings, commit with a clear message, and push.

## Update the library from Screvi (no export needed)

1. Call the Screvi MCP tool `list-sources` with `types: ["book"]`, `limit: 200`
   (page with `offset` if `total` is larger). It returns every book with its highlight
   count and no highlight text.
2. Save the result as `data/screvi_sources_snapshot.json`, keeping the existing format:
   `{"fetched": "<date>", "via": "...", "sources": [{"id","name","author","asin","isbn","count","last"}, ...]}`
   with `last` = date of `last_highlight_at`.
3. Compare with the previous snapshot (git diff) and tell Davide what changed: new
   books, new highlights, sources that look like file names, papers or a second copy of
   a book. Propose a title/author/kind for each unclear one and add the rows he confirms
   to `data/screvi_sources.csv`.
4. Offer to clean up Screvi itself with `update-source`: proper titles for file-name
   sources (title edits are kept by Screvi across re-imports), and ISBNs for books whose
   ISBN in `books.csv` is reliable (from My Library, `manual.csv`, an override or an exact
   ISBN lookup — not one borrowed by `enrich_openlibrary.py`'s title search).
5. `python import_screvi.py ../data/screvi_sources_snapshot.json ../data/screvi.csv`,
   then `python merge.py`, `python enrich_openlibrary.py`, `python merge.py`,
   `python build_site.py`; commit and push.

A Screvi CSV export (`data/raw/screvi-highlights-*.csv`) still works with the same
importer and can also detect duplicate highlights, which the snapshot cannot: Screvi
skips new duplicates itself, but older ones (e.g. in *Pandas for Everyone*) inflate
its counts until they are deleted in the app.

## Add a summary for a book

1. Find the book in `data/books.csv` (search title and author, case-insensitive). If it is
   not there, add it first (see "Add a book"). If several match, ask which one.
2. Show what is already in `data/notes.csv` for that id, if anything.
3. Ask Davide, in one message:
   - the year(s) he read it (several years separated by `;`), if not already known
   - whether it is a must-read
   - the summary: one or two sentences in his voice. Offer to draft one from his Screvi
     highlights for that book (use the Screvi search tool with `sourceQuery` set to the
     title) or from his long notes; a draft must be shown to him and approved before saving.
4. Write the row in `data/notes.csv` (create or update; `summary_status` = `mine` if he
   wrote it, `draft` if he approved a draft without rewriting; `todo` = 0 once there is a summary).
5. If he gives longer notes too, save them in `data/private/notes/<id>.md` and run
   `LIBRARY_PASSWORD=... python scripts/private_notes.py encrypt` (in a fresh clone,
   run `decrypt` first so existing notes are not lost).
6. Rebuild, commit, push. Tell him it is on the Reading history tab.

## Add a book

1. With an ISBN: `cd scripts && python add_book.py <isbn>` shows what Open Library knows.
   Show it to Davide; if right, rerun with `--write` (add `--marks N` if he gives a count).
   If Open Library does not know the ISBN, ask for title and author and pass `--title`/`--author`.
2. Without an ISBN: ask for title and author, check `data/books.csv` for a near match
   first (it may already be there under a slightly different title), then add the row
   to `data/manual.csv` by hand with `id` = `<authorlastname>-<title-slug>`.
3. Run `python enrich_openlibrary.py` to fill a missing page count, then merge, build, commit.

## Import new My Library exports

1. Davide drops files into `data/raw/` on his laptop (repo checkout at
   `C:\Users\Davide\sw_dev\gerbaudo-library`). Stage them into this session with the
   device tools if the laptop is linked, otherwise ask him to attach them.
2. `python import_mylibrary.py ../data/raw/mylibrary-YYYYMM.db ../data/mylibrary-YYYYMM.csv`.
3. `python merge.py`, then read `data/merge_log.csv` and report anything surprising
   (counts that went down, unexpected merges) before committing. Ask if unsure.
4. `python enrich_openlibrary.py && python merge.py && python build_site.py`, commit, push.

## Push quotes to Screvi

1. Find the book with `list-sources` (`query` = title). If it is not in Screvi, create it
   with `create-source` (name, author, ISBN when reliable); it returns the existing source
   instead of a duplicate when one matches.
2. Add the quotes with `create-highlights` (up to 100 per call; passages already there are
   skipped, so a repeated push is safe). Put the page number in `location` and in the note
   (`p. 123`), and tag the batch so it is easy to find.
3. Never push quotes that already come from Kindle.

## Publish

GitHub Pages serves `docs/` from `main`; pushing is enough. The private Claude artifact
preview ("Gerbaudo Library") can be refreshed by publishing the body written by
`python build_site.py <path>`.
