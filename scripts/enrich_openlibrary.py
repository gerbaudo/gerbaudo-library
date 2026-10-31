"""Fill missing page counts (and ISBNs, for covers) from Open Library.

Usage:
    python scripts/enrich_openlibrary.py          # only books not yet looked up
    python scripts/enrich_openlibrary.py --retry  # also retry earlier misses

Results are cached in data/openlibrary.csv (one row per book id) so lookups are
done once; merge.py reads the cache and fills gaps, never overwriting imported values.

  - Books with an ISBN: the edition's own number_of_pages.
  - Books without (e.g. Kindle): a title + author search; the page count is the
    median across editions (method = "search"), and an ISBN is borrowed for the cover.
"""

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from common import match_key, normalize_isbn

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE = os.path.join(DATA, "openlibrary.csv")
FIELDS = ["id", "pages", "isbn", "ol_key", "method"]
HEADERS = {"User-Agent": "gerbaudo-library/0.1 (davide.gerbaudo@gmail.com)"}


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def by_isbn(isbns):
    keys = ",".join(f"ISBN:{i}" for i in isbns)
    data = get_json(f"https://openlibrary.org/api/books?bibkeys={keys}&format=json&jscmd=data")
    out = {}
    for i in isbns:
        d = data.get(f"ISBN:{i}")
        if d:
            out[i] = {"pages": d.get("number_of_pages", ""), "ol_key": d.get("key", "")}
    return out


def clean_title(title):
    t = re.split(r"[:(\[]", title)[0]
    return re.sub(r"\s+", " ", t).strip()


def by_search(title, author):
    last = author.split(" and ")[0].split()[-1] if author.strip() else ""
    q = {"title": clean_title(title), "fields": "key,title,author_name,number_of_pages_median,isbn",
         "limit": "5"}
    if last:
        q["author"] = last
    docs = get_json("https://openlibrary.org/search.json?" + urllib.parse.urlencode(q)).get("docs", [])
    want = match_key(title, author).split("|")[0]
    for d in docs:
        # accept only a title that matches our loose key, to avoid wrong books
        if match_key(d.get("title", "")).split("|")[0] != want:
            continue
        isbn13 = next((i for i in d.get("isbn", []) if len(i) == 13), None)
        return {"pages": d.get("number_of_pages_median") or "", "ol_key": d.get("key", ""),
                "isbn": normalize_isbn(isbn13) or ""}
    return None


def main():
    retry = "--retry" in sys.argv
    with open(os.path.join(DATA, "books.csv"), newline="", encoding="utf-8") as fh:
        books = list(csv.DictReader(fh))
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, newline="", encoding="utf-8") as fh:
            cache = {r["id"]: r for r in csv.DictReader(fh)}

    todo = [b for b in books
            if b["pages"] in ("", "0") or not b["isbn"]]
    todo = [b for b in todo if b["id"] not in cache or (retry and cache[b["id"]]["method"] == "miss")]
    print(f"{len(todo)} books to look up")

    with_isbn = [b for b in todo if b["isbn"]]
    for i in range(0, len(with_isbn), 40):
        chunk = with_isbn[i:i + 40]
        found = by_isbn([b["isbn"] for b in chunk])
        for b in chunk:
            f = found.get(b["isbn"])
            if f and f["pages"]:
                cache[b["id"]] = {"id": b["id"], "pages": f["pages"], "isbn": b["isbn"],
                                  "ol_key": f["ol_key"], "method": "isbn"}
            else:
                with_isbn_miss = b
                with_isbn_miss["_fallback"] = True
        time.sleep(1)

    for b in [b for b in todo if not b["isbn"] or b.get("_fallback")]:
        try:
            f = by_search(b["title"], b["author"])
        except Exception as e:  # network hiccup: leave for next run
            print("  error", b["title"], e)
            continue
        if f:
            cache[b["id"]] = {"id": b["id"], "pages": f["pages"], "isbn": b["isbn"] or f["isbn"],
                              "ol_key": f["ol_key"], "method": "search"}
        else:
            cache[b["id"]] = {"id": b["id"], "pages": "", "isbn": "", "ol_key": "", "method": "miss"}
        time.sleep(0.7)

    with open(CACHE, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(sorted(cache.values(), key=lambda r: r["id"]))
    got = sum(1 for r in cache.values() if r["pages"])
    print(f"cache: {len(cache)} books, {got} with pages")


if __name__ == "__main__":
    main()
