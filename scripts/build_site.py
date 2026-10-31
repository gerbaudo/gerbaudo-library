"""Build the static viewer from data/books.csv.

Usage:
    python scripts/build_site.py [fragment_out]

Writes docs/index.html (a full page for GitHub Pages) with the book data embedded,
so the page works offline and needs no server. Optionally also writes the bare page
body (no <html>/<head> wrapper) to fragment_out, used for the Claude artifact preview.
"""

import csv
import datetime
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")


def num(v):
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def main():
    with open(os.path.join(ROOT, "data", "books.csv"), newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    books = [{
        "id": r["id"], "isbn": r["isbn"], "title": r["title"], "author": r["author"],
        "pages": num(r["pages"]), "ps": "est" if r["pages_source"] == "openlibrary-search" else "",
        "pub": r["published"], "cat": r["categories"],
        "marks": num(r["marks"]) or 0, "oneshot": num(r["oneshot"]) or 0, "hl": num(r["highlights"]) or 0,
        "src": r["sources"],
    } for r in rows]

    with open(os.path.join(ROOT, "docs", "template.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    data = json.dumps(books, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = tpl.replace("__BOOKS_JSON__", data).replace("__UPDATED__", datetime.date.today().isoformat())

    page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            "<style>html,body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n"
            "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as fh:
            fh.write(body)
    print(f"built docs/index.html with {len(books)} books")


if __name__ == "__main__":
    main()
