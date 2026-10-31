"""Import books from a "My Library" (Android app) SQLite export.

Usage:
    python scripts/import_mylibrary.py data/raw/mylibrary-2021.db data/mylibrary-2021.csv

Name the output data/mylibrary-<date>.csv: merge.py reads every such snapshot,
oldest first (by file name), and combines them.

The app stores per-book counters in the COMMENTS column as JSON, e.g.
    [{"title": "Marks", "content": "30"}, {"title": "Oneshot", "content": "50"}]
Each counter becomes its own column (marks, oneshot, skip, ...).
"""

import csv
import json
import re
import sqlite3
import sys

from common import book_id, normalize_isbn


def parse_json(value, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def clean(text) -> str:
    """Strip zero-width characters the app sometimes inserts, and squeeze spaces."""
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def counters(comments) -> dict:
    out = {}
    for item in parse_json(comments, []):
        if isinstance(item, dict) and item.get("title"):
            key = item["title"].strip().lower()
            # the app data has a few spelling variants of the same counter
            key = {"mark": "marks", "marksman": "marks"}.get(key, key)
            try:
                out[key] = int(str(item.get("content", "")).strip())
            except ValueError:
                pass
    return out


def main(db_path: str, out_path: str) -> None:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT b.*, TRIM(COALESCE(a.FIRSTNAME, '') || ' ' || COALESCE(a.LASTNAME, '')) AS author_name
        FROM BOOK b LEFT JOIN AUTHOR a ON a.ID = b.AUTHOR
        WHERE COALESCE(b.IN_WISHLIST, 0) = 0
        """
    ).fetchall()

    fields = ["id", "isbn", "title", "author", "pages", "publisher", "published",
              "categories", "read", "marks", "oneshot", "source"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            isbn = normalize_isbn(r["ISBN"])
            title, author = clean(r["TITLE"]), clean(r["author_name"])
            c = counters(r["COMMENTS"])
            writer.writerow({
                "id": book_id(isbn, title, author),
                "isbn": isbn or "",
                "title": title,
                "author": author,
                "pages": r["PAGES"] or "",
                "publisher": clean(r["PUBLISHER"]),
                "published": (r["PUBLISHED_DATE"] or "").strip(),
                "categories": "; ".join(parse_json(r["CATEGORIES"], [])),
                "read": int(r["READ"] or 0),
                "marks": c.get("marks", ""),
                "oneshot": c.get("oneshot", ""),
                "source": "mylibrary",
            })
    print(f"wrote {len(rows)} books to {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
