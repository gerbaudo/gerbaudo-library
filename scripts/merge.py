"""Merge per-source CSVs into data/books.csv, the single source of truth.

Usage:
    python scripts/merge.py

Reads data/mylibrary.csv and data/screvi.csv. Matching, in order:
  1. same id (ISBN-13 when known)
  2. same loose key (main title + author last name)
Identical duplicate rows are collapsed. Books that share a title and author but
have different ISBNs are kept apart and listed in data/needs_review.csv, so a
human decides whether they are two editions or one book entered twice.

Manual decisions can go in data/overrides.csv (columns: id, field, value); they are
applied last and win over any import.
"""

import csv
import os
from collections import defaultdict

from common import match_key

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
FIELDS = ["id", "isbn", "asin", "title", "author", "pages", "published", "categories",
          "read", "marks", "oneshot", "highlights", "sources", "pages_source"]


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    books: dict[str, dict] = {}
    by_key: dict[str, str] = {}
    review = []

    # 1. My Library: paper books, with ISBN and page marks
    for r in load("mylibrary.csv"):
        row = {f: r.get(f, "") for f in FIELDS}
        row["sources"] = "mylibrary"
        row["pages_source"] = "mylibrary" if row["pages"] not in ("", "0") else ""
        if r["id"] in books:
            if all(books[r["id"]][f] == row[f] for f in FIELDS):
                continue  # exact duplicate scan
            review.append({"id": r["id"], "other_id": r["id"], "title": r["title"],
                           "reason": "same ISBN entered twice with different data"})
            continue
        key = match_key(r["title"], r["author"])
        if key in by_key:
            review.append({"id": r["id"], "other_id": by_key[key], "title": r["title"],
                           "reason": "same title and author, different ISBN (two editions?)"})
        books[r["id"]] = row
        by_key.setdefault(key, r["id"])

    # 2. Screvi: Kindle/ebook highlights, matched by title + author
    for r in load("screvi.csv"):
        key = match_key(r["title"], r["author"])
        target = books.get(by_key.get(key, ""))
        if target:
            target["highlights"] = r["highlights"]
            target["asin"] = target["asin"] or r["asin"]
            target["sources"] += ";screvi"
        else:
            row = {f: "" for f in FIELDS}
            row.update(id=r["id"], asin=r["asin"], title=r["title"], author=r["author"],
                       highlights=r["highlights"], read="1", sources="screvi")
            books[r["id"]] = row
            by_key[key] = r["id"]

    # 3. Open Library cache fills gaps only (never overwrites imported values)
    for o in load("openlibrary.csv"):
        b = books.get(o["id"])
        if not b:
            continue
        if b["pages"] in ("", "0") and o["pages"]:
            b["pages"] = o["pages"]
            b["pages_source"] = "openlibrary-" + o["method"]
        if not b["isbn"] and o["isbn"]:
            b["isbn"] = o["isbn"]

    # 4. Manual overrides win
    for o in load("overrides.csv"):
        if o["id"] in books and o["field"] in FIELDS:
            books[o["id"]][o["field"]] = o["value"]

    rows = sorted(books.values(), key=lambda b: (b["author"].split()[-1:] or [""])[0].lower())
    with open(os.path.join(DATA, "books.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(DATA, "needs_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "other_id", "title", "reason"])
        w.writeheader()
        w.writerows(review)

    both = sum(1 for b in rows if ";" in b["sources"])
    print(f"books.csv: {len(rows)} books ({both} in both sources); "
          f"needs_review.csv: {len(review)} items")


if __name__ == "__main__":
    main()
