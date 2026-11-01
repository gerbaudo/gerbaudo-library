# gerbaudo-library

My personal library: the books I own and read, with a simple measure of how much
each one gave me — the number of passages I marked or highlighted, compared with
its length.

Published at <https://gerbaudo.github.io/gerbaudo-library> (coming soon).

## How it works

- **One data file** is the source of truth: `data/books.csv`, one row per book.
- **Importers** in `scripts/` turn each source into the same columns:
  - `import_mylibrary.py` — the *My Library* Android app's SQLite export
    (page marks are stored in its Comments field)
  - `import_screvi.py` — a [Screvi](https://screvi.com) highlights CSV export
    (Screvi also syncs Kindle); only per-book counts are kept
  - `merge.py` — combines them into `data/books.csv` and lists doubtful matches in
    `data/needs_review.csv`; manual fixes go in `data/overrides.csv`

- **Matching** (`scripts/common.py`): every book gets a stable ID — its ISBN-13 when
  known, otherwise an `author-title` slug. Uncertain matches go to a review list
  instead of being merged silently.
- **Viewer**: `docs/index.html`, a single static page (shelf of spines, search,
  and a marks-versus-pages chart) built by `build_site.py` from `docs/template.html`.
  GitHub Pages serves it from the `docs/` folder.

## Refreshing the data

```
# drop new exports into data/raw/, then:
cd scripts
python import_mylibrary.py ../data/raw/mylibrary-YYYYMM.db ../data/mylibrary-YYYYMM.csv   # one per snapshot
python import_screvi.py ../data/raw/screvi-highlights-YYYY-MM-DD.csv ../data/screvi.csv
python merge.py
python enrich_openlibrary.py   # look up missing pages/ISBNs (cached in data/openlibrary.csv)
python merge.py                # re-merge to apply them
python build_site.py           # rebuild docs/index.html (the viewer)
```

The `pages_source` column says where each page count came from: `mylibrary` (my
own entry), `openlibrary-isbn` (that exact edition), or `openlibrary-search` (median
across editions of the title: an estimate, fine for Kindle books).
## Summaries, reading history, long notes

- `data/notes.csv`: for each book I've written about, the year(s) I read it, whether
  it's a must-read, and a one- or two-sentence summary in my own words. These are
  public and appear on the **Reading history** tab and in each book's details.
- Long notes (chapter notes, older reviews) are kept in `data/private/notes/`
  (git-ignored) and committed only as an encrypted bundle,
  `data/notes_private.enc.json` (`scripts/private_notes.py encrypt|decrypt`). The page
  shows them behind a password. This is protection against scraping, not real secrecy.
- **Password hint:** it is not stored anywhere in this repo. It was chosen in the
  Claude conversation where this library was set up (November 2026): ask Claude to
  search my past chats for "library notes password". Run the script with
  `LIBRARY_PASSWORD=... python scripts/private_notes.py decrypt`, or type it when asked.
- Quotes live in [Screvi](https://screvi.com), not in this repo.
- `data/manual.csv`: books added by hand, e.g. with `scripts/add_book.py <isbn>`.
- `.claude/skills/library/SKILL.md` describes these workflows for Claude
  ("add a summary for …", "add ISBN …", "import the new exports").

## Privacy

Raw exports live in `data/raw/`, which is git-ignored: they contain full highlight
text and personal notes. Only counts and public metadata are committed. Long notes are
published only in encrypted form.
