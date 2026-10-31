"""Merge per-source CSVs into data/books.csv, the single source of truth.

Usage:
    python scripts/merge.py

Reads every data/mylibrary-*.csv snapshot (oldest first) and data/screvi.csv.
Matching, in order:
  1. same id (ISBN-13 when known)
  2. same loose key (main title + author last name)
Across snapshots, a match is the same book scanned again: marks keep the larger
value. Within one snapshot, the same title with different ISBNs is kept as two
books. Anything doubtful is listed in data/needs_review.csv for a human to decide.

Manual decisions can go in data/overrides.csv (columns: id, field, value); they are
applied last and win over any import.
"""

import csv
import os
import re

from common import match_key, same_volume

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
FIELDS = ["id", "isbn", "asin", "title", "author", "pages", "published", "categories",
          "read", "marks", "oneshot", "highlights", "sources", "pages_source"]


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


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

    # 1. My Library snapshots (paper books, page marks), oldest first.
    #    A later snapshot re-scans many of the same books: match by ISBN, or by
    #    title + author when the ISBN differs or is missing. Counters keep the
    #    larger value (marks only grow as I read); metadata fills gaps.
    snapshots = sorted(f for f in os.listdir(DATA) if re.fullmatch(r"mylibrary-.+\.csv", f))
    for snap in snapshots:
        seen_here: dict[str, str] = {}   # key -> id, within this snapshot
        title_here: dict[str, str] = {}  # key -> title as written in this snapshot
        for r in load(snap):
            row = {f: r.get(f, "") for f in FIELDS}
            row["sources"] = "mylibrary"
            row["pages_source"] = "mylibrary" if row["pages"] not in ("", "0") else ""
            key = match_key(r["title"], r["author"])
            if (key in seen_here and seen_here[key] != r["id"]
                    and same_volume(r["title"], title_here[key])):
                # same title twice in ONE scan with different ISBNs: two editions, or two copies?
                review.append({"id": r["id"], "other_id": seen_here[key], "title": r["title"],
                               "reason": f"same title and author, different ISBN ({snap})"})
            title_here.setdefault(key, r["title"])
            existing_id = r["id"] if r["id"] in books else None
            if (existing_id is None and key in by_key and key not in seen_here
                    and same_volume(r["title"], books[by_key[key]]["title"])):
                existing_id = by_key[key]  # re-scan from an earlier snapshot, different/no ISBN
            if existing_id is None or existing_id in seen_here.values():
                books[r["id"]] = row
                by_key.setdefault(key, r["id"])
                seen_here.setdefault(key, r["id"])
                continue
            seen_here.setdefault(key, existing_id)
            old = books[existing_id]
            for f in ("marks", "oneshot"):
                a, b = to_int(old[f]), to_int(row[f])
                if a is not None and b is not None and b < a:
                    review.append({"id": existing_id, "other_id": "", "title": old["title"],
                                   "reason": f"{f} went down from {a} to {b} in {snap}; kept {a}"})
                if b is not None and (a is None or b > a):
                    old[f] = row[f]
            old["read"] = str(max(to_int(old["read"]) or 0, to_int(row["read"]) or 0))
            for f in ("isbn", "pages", "published", "categories"):
                if not old[f] or old[f] == "0":
                    old[f] = row[f]
            if not old["pages_source"] and row["pages_source"]:
                old["pages_source"] = row["pages_source"]
            if len(row["author"]) > len(old["author"]):  # prefer "Edward R. Tufte" over "Tufte"
                old["author"] = row["author"]

    # 2. Screvi: Kindle/ebook highlights, matched by title + author
    for r in load("screvi.csv"):
        key = match_key(r["title"], r["author"])
        target = books.get(by_key.get(key, ""))
        if target and same_volume(r["title"], target["title"]):
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
