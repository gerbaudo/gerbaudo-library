"""Aggregate a Screvi highlights CSV export into one row per book.

Usage:
    python scripts/import_screvi.py data/raw/screvi-highlights-YYYY-MM-DD.csv data/screvi.csv

Only counts and metadata are written; the highlight text never leaves data/raw/.
"""

import csv
import sys
from collections import defaultdict

from common import book_id


def main(in_path: str, out_path: str) -> None:
    books = defaultdict(lambda: {"highlights": 0, "notes": 0, "favorites": 0, "dates": []})
    with open(in_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if (row.get("Type") or "").strip().lower() != "book":
                continue
            key = (row["Source"].strip(), row["Author"].strip())
            b = books[key]
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


if __name__ == "__main__":
    main(*sys.argv[1:3])
