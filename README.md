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
  - `import_screvi.py` — highlights from [Screvi](https://screvi.com), which also
    syncs Kindle *(to do)*
- **Matching** (`scripts/common.py`): every book gets a stable ID — its ISBN-13 when
  known, otherwise an `author-title` slug. Uncertain matches go to a review list
  instead of being merged silently.
- **Covers** are linked from Open Library by ISBN, not stored here.

## Privacy

Raw exports live in `data/raw/`, which is git-ignored: they contain full highlight
text and personal notes. Only counts and public metadata are committed. Private
notes and highlights will go into an encrypted file, readable on a
password-protected page.
