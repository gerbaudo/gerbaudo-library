"""Shared helpers: stable book IDs and normalisation used by every importer."""

import re
import unicodedata


def isbn10_to_13(isbn10: str) -> str:
    core = "978" + isbn10[:9]
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(core))
    return core + str((10 - total % 10) % 10)


def normalize_isbn(raw) -> str | None:
    """Return an ISBN-13 string, or None if the value is not a usable ISBN."""
    if not raw:
        return None
    s = re.sub(r"[^0-9Xx]", "", str(raw)).upper()
    if len(s) == 13 and s.startswith(("978", "979")):
        return s
    if len(s) == 10:
        return isbn10_to_13(s)
    return None


def slugify(text: str, max_words: int = 6) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:max_words])


def match_key(title: str, author: str = "") -> str:
    """Loose key for fuzzy matching across sources: main title (before ':' or '('),
    lowercase ascii, plus the author's last name."""
    main = re.split(r"[:(\[]", title or "")[0]
    last = (author or "").strip().split()[-1] if (author or "").strip() else ""
    return slugify(main, 8) + "|" + slugify(last, 1)


def book_id(isbn13: str | None, title: str, author: str = "") -> str:
    """Stable ID: the ISBN-13 when known, otherwise author-title slug."""
    if isbn13:
        return isbn13
    last = (author or "").strip().split()[-1] if (author or "").strip() else "unknown"
    return slugify(last, 1) + "-" + slugify(title, 5)
