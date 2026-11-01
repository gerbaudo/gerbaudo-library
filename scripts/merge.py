"""Merge per-source CSVs into data/books.csv, the single source of truth.

Usage:
    python scripts/merge.py

Reads every data/mylibrary-*.csv snapshot (oldest first) and data/screvi.csv.
Matching, in order:
  1. same id (ISBN-13 when known)
  2. same loose key (main title + author last name)
A match is the same book, kept once: within one snapshot the largest mark count
wins, across snapshots the newer count wins. Every merge decision is written to
data/merge_log.csv. For books in both sources (paper + Kindle), the viewer uses
the larger of marks and highlights, never the sum.

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
    by_key: dict[str, list[str]] = {}
    log = []

    # 1. My Library snapshots (paper books, page marks), oldest first.
    #    Rules (decided by me, Oct 2026):
    #      - same book = same ISBN, or same title + first author (and no clashing
    #        volume number), even with different ISBNs: kept once
    #      - duplicates within one snapshot: keep the largest mark count
    #      - across snapshots: the newer snapshot's count wins when it has one
    #    Metadata from later scans only fills gaps. Every merge is logged in
    #    data/merge_log.csv so it can be checked.
    def find(rid, key, title):
        if rid in books:
            return rid
        return next((i for i in by_key.get(key, []) if same_volume(title, books[i]["title"])), None)

    snapshots = sorted(f for f in os.listdir(DATA) if re.fullmatch(r"mylibrary-.+\.csv", f))
    # data/manual.csv (books added by hand, e.g. from the old reading list or by ISBN)
    # is read last, like the newest snapshot
    if os.path.exists(os.path.join(DATA, "manual.csv")):
        snapshots.append("manual.csv")
    for snap in snapshots:
        rows_in = load(snap)
        # books already known by ISBN go first, so the title/author spellings they
        # carry in this scan are registered before the rest are matched
        rows_in.sort(key=lambda r: r["id"] not in books)
        for r in rows_in:
            row = {f: r.get(f, "") for f in FIELDS}
            row["sources"] = "manual" if snap == "manual.csv" else "mylibrary"
            row["pages_source"] = row["sources"] if row["pages"] not in ("", "0") else ""
            key = match_key(r["title"], r["author"])
            existing_id = find(r["id"], key, r["title"])
            if existing_id is None:
                row["_snap"] = snap
                books[r["id"]] = row
                by_key.setdefault(key, []).append(r["id"])
                continue
            old = books[existing_id]
            if existing_id not in by_key.setdefault(key, []):
                by_key[key].append(existing_id)  # remember this spelling of title/author
            if row == {f: old.get(f, "") for f in FIELDS}:
                continue  # identical scan
            for f in ("marks", "oneshot"):
                a, b = to_int(old[f]), to_int(row[f])
                if b is None or a == b:
                    continue
                if old["_snap"] == snap:      # duplicate inside one scan: largest wins
                    keep = max(a or 0, b)
                    note = "duplicate in one scan, kept the largest"
                else:                          # later scan: newer wins
                    keep = b
                    note = "newer scan wins"
                if a is not None:
                    log.append({"id": existing_id, "other_id": r["id"], "title": old["title"],
                                "decision": f"{f}: {a} vs {b} -> {keep} ({note}, {snap})"})
                old[f] = str(keep)
            if r["id"] != existing_id:
                log.append({"id": existing_id, "other_id": r["id"], "title": old["title"],
                            "decision": f"merged as the same book ({snap})"})
            old["_snap"] = snap
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
        tid = find(None, key, r["title"])
        target = books.get(tid) if tid else None
        if target:
            target["highlights"] = r["highlights"]
            target["asin"] = target["asin"] or r["asin"]
            target["sources"] += ";screvi"
        else:
            row = {f: "" for f in FIELDS}
            row.update(id=r["id"], asin=r["asin"], title=r["title"], author=r["author"],
                       highlights=r["highlights"], read="1", sources="screvi")
            books[r["id"]] = row
            by_key.setdefault(key, []).append(r["id"])

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
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(DATA, "merge_log.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "other_id", "title", "decision"])
        w.writeheader()
        w.writerows(log)

    both = sum(1 for b in rows if ";" in b["sources"])
    print(f"books.csv: {len(rows)} books ({both} in both sources); "
          f"merge_log.csv: {len(log)} decisions")


if __name__ == "__main__":
    main()
