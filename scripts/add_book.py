"""Add a book to data/manual.csv by ISBN, using Open Library for the details.

Usage:
    python scripts/add_book.py 9780345331359            # look up and show, ask nothing, write nothing
    python scripts/add_book.py 9780345331359 --write    # append to data/manual.csv
    python scripts/add_book.py 9780345331359 --write --marks 12 --title "Cosmos" --author "Carl Sagan"

--title/--author/--pages override what Open Library returns (or fill it in when
Open Library does not know the ISBN). Then run merge.py and build_site.py.
"""

import argparse
import csv
import json
import os
import sys
import urllib.request

from common import book_id, normalize_isbn

ROOT = os.path.join(os.path.dirname(__file__), "..")
MANUAL = os.path.join(ROOT, "data", "manual.csv")
FIELDS = ["id", "isbn", "title", "author", "pages", "publisher", "published", "categories",
          "read", "marks", "oneshot", "source"]


def lookup(isbn):
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    req = urllib.request.Request(url, headers={"User-Agent": "gerbaudo-library/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r).get(f"ISBN:{isbn}")
    if not d:
        return {}
    return {
        "title": d.get("title", "") + (": " + d["subtitle"] if d.get("subtitle") else ""),
        "author": " and ".join(a["name"] for a in d.get("authors", [])),
        "pages": d.get("number_of_pages", ""),
        "publisher": ", ".join(p["name"] for p in d.get("publishers", [])),
        "published": d.get("publish_date", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("isbn")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--title"); ap.add_argument("--author"); ap.add_argument("--pages")
    ap.add_argument("--marks", default="")
    a = ap.parse_args()

    isbn = normalize_isbn(a.isbn)
    if not isbn:
        sys.exit(f"not a valid ISBN: {a.isbn}")
    info = lookup(isbn)
    for f in ("title", "author", "pages"):
        if getattr(a, f):
            info[f] = getattr(a, f)
    if not info.get("title"):
        sys.exit(f"Open Library does not know {isbn}; pass --title and --author")
    row = {f: "" for f in FIELDS}
    row.update(info, id=isbn, isbn=isbn, read=1, marks=a.marks, source="manual")
    print(json.dumps(row, ensure_ascii=False, indent=1))

    if a.write:
        existing = []
        if os.path.exists(MANUAL):
            with open(MANUAL, newline="", encoding="utf-8") as fh:
                existing = list(csv.DictReader(fh))
        if any(r["id"] == isbn for r in existing):
            sys.exit(f"{isbn} is already in data/manual.csv")
        with open(MANUAL, "a" if existing else "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            if not existing:
                w.writeheader()
            w.writerow(row)
        print("added to data/manual.csv")


if __name__ == "__main__":
    main()
