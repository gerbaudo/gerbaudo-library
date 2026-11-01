---
name: library
description: Maintain Davide's book library in this repo. Use when he asks to add a summary for a book, add a book (by ISBN or title), import new My Library / Screvi exports, push quotes to Screvi, or rebuild and publish the library page.
---

# Gerbaudo Library

The library is a static page (`docs/index.html`, served by GitHub Pages at
https://gerbaudo.github.io/gerbaudo-library) built from CSV files. Read `README.md`
for the full pipeline. Key files:

| File | What it is | Edited by |
|---|---|---|
| `data/mylibrary-<date>.csv` | My Library app snapshots (paper books, page marks) | importer |
| `data/screvi.csv` | per-book highlight counts from a Screvi export | importer |
| `data/manual.csv` | books added by hand | `add_book.py` or by hand |
| `data/notes.csv` | `id, title, years_read, must_read, todo, summary_status, summary` (public) | by hand / this skill |
| `data/private/notes/<id>.md` | long notes, git-ignored | by hand |
| `data/notes_private.enc.json` | encrypted long notes (committed, shown behind a password) | `private_notes.py` |
| `data/overrides.csv` | `id, field, value` manual fixes that always win | by hand |
| `data/books.csv` | merged result — never edit, regenerate with `merge.py` | `merge.py` |

Rules already decided by Davide:
- Same book in two My Library scans: the newer count wins. Same title and author twice
  in one scan: keep one, with the largest count.
- Paper marks and Kindle highlights of the same book: use the larger, never the sum.
- Book quotes go to Screvi, not to this repo. Summaries are public and in his own words.
  Long notes are private (encrypted). The password is not in the repo: ask Davide, or
  search his past Claude chats for "library notes password". Never write it into a file.

Always finish a change with: `cd scripts && python merge.py && python build_site.py`,
check the output for warnings, commit with a clear message, and push.

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

## Import new exports

1. Davide drops files into `data/raw/` on his laptop (repo checkout at
   `C:\Users\Davide\sw_dev\gerbaudo-library`). Stage them into this session with the
   device tools if the laptop is linked, otherwise ask him to attach them.
2. My Library: `python import_mylibrary.py ../data/raw/mylibrary-YYYYMM.db ../data/mylibrary-YYYYMM.csv`.
   Screvi: `python import_screvi.py ../data/raw/screvi-highlights-YYYY-MM-DD.csv ../data/screvi.csv`.
3. `python merge.py`, then read `data/merge_log.csv` and report anything surprising
   (counts that went down, unexpected merges) before committing. Ask if unsure.
4. `python enrich_openlibrary.py && python merge.py && python build_site.py`, commit, push.

## Push quotes to Screvi

The Screvi connector can add highlights to an existing Screvi book (`source_id`) but cannot
create the book itself. Ask Davide to create the book in the Screvi app and send its URL
(`app.screvi.com/sources/<id>`). Put the page reference in the note (`p. 123`) and tag the
highlights so the batch is easy to find. Never push quotes that already come from Kindle.

## Publish

GitHub Pages serves `docs/` from `main`; pushing is enough. The private Claude artifact
preview ("Gerbaudo Library") can be refreshed by publishing the body written by
`python build_site.py <path>`.
