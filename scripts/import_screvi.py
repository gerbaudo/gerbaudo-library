"""Aggregate a Screvi highlights CSV export into one row per book.

Usage:
    python scripts/import_screvi.py data/raw/screvi-highlights-YYYY-MM-DD.csv data/screvi.csv

Only counts and metadata are written; the highlight text never leaves data/raw/.

data/screvi_sources.csv maps messy Screvi source names (file names from PDFs sent
to the Kindle, two names for one book) to a proper title and author, and marks
papers/articles (kind = paper) so they stay out of the book library. Exact
duplicate highlights (same text in the same book) are counted once.
"""

import csv
import os
import sys
from collections import defaultdict

MAP = os.path.join(os.path.dirname(__file__), "..", "data", "screvi_sources.csv")


def load_map():
    if not os.path.exists(MAP):
        return {}
    with open(MAP, newline="", encoding="utf-8") as fh:
        return {r["screvi_source"].strip(): r for r in csv.DictReader(fh)}

from common import book_id


def main(in_path: str, out_path: str) -> None:
    mapping = load_map()
    books = defaultdict(lambda: {"highlights": 0, "notes": 0, "favorites": 0, "dates": [], "seen": set()})
    skipped = defaultdict(int)
    with open(in_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if (row.get("Type") or "").strip().lower() != "book":
                continue
            src, author = row["Source"].strip(), row["Author"].strip()
            m = mapping.get(src)
            if m and m["kind"] != "book":
                skipped[src] += 1
                continue
            if m and m["title"]:
                src, author = m["title"], m["author"] or author
            key = (src, author)
            b = books[key]
            text = (row.get("Highlight") or "").strip()
            if text in b["seen"]:
                continue  # exact duplicate (e.g. the same clipping imported twice)
            b["seen"].add(text)
            b["highlights"] += 1
            b["notes"] += bool((row.get("Note") or "").strip())
            b["favorites"] += (row.get("Favorite") or "").strip().lower() == "yes"
            if row.get("Date"):
                b["dates"].append(row["Date"][:10])
            if row.get("ASIN"):
                b["asin"] = row["ASIN"].strip()

    fields = ["id", "title", "author", "asin", "highlights", "notes", "favorites",
              "first_highlight", "last_highlight", "source"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for (title, author), b in sorted(books.items(), key=lambda kv: -kv[1]["highlights"]):
            writer.writerow({
                "id": book_id(None, title, author),
                "title": title,
                "author": author,
                "asin": b.get("asin", ""),
                "highlights": b["highlights"],
                "notes": b["notes"],
                "favorites": b["favorites"],
                "first_highlight": min(b["dates"]) if b["dates"] else "",
                "last_highlight": max(b["dates"]) if b["dates"] else "",
                "source": "screvi",
            })
    print(f"wrote {len(books)} books ({sum(b['highlights'] for b in books.values())} highlights) to {out_path}")
    if skipped:
        print(f"left out {len(skipped)} papers/articles ({sum(skipped.values())} highlights), see data/screvi_sources.csv")


if __name__ == "__main__":
    main(*sys.argv[1:3])
