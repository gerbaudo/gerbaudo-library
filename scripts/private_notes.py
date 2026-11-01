"""Long notes: plain text stays local, only an encrypted bundle is committed.

Usage:
    python scripts/private_notes.py encrypt   # data/private/notes/*.md -> data/notes_private.enc.json
    python scripts/private_notes.py decrypt   # the reverse, e.g. in a fresh clone

The plain notes in data/private/ are git-ignored. The committed bundle is AES-GCM
encrypted with a key derived (PBKDF2-SHA256) from a password, so the web page can
decrypt it in the browser after asking for the password. This is light protection
against scraping and casual reading, not real secrecy: the default password is
written here. Set LIBRARY_PASSWORD to use another one.
"""

import base64
import glob
import json
import os
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = os.path.join(os.path.dirname(__file__), "..")
PLAIN = os.path.join(ROOT, "data", "private", "notes")
BUNDLE = os.path.join(ROOT, "data", "notes_private.enc.json")
ITERATIONS = 200_000


def password() -> bytes:
    return os.environ.get("LIBRARY_PASSWORD", "dglibrary").encode()


def key(salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return kdf.derive(password())


def encrypt():
    notes = {}
    for path in sorted(glob.glob(os.path.join(PLAIN, "*.md"))):
        with open(path, encoding="utf-8") as fh:
            notes[os.path.basename(path)[:-3]] = fh.read()
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(key(salt)).encrypt(iv, json.dumps(notes, ensure_ascii=False).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    with open(BUNDLE, "w", encoding="utf-8") as fh:
        json.dump({"v": 1, "kdf": "PBKDF2-SHA256", "iterations": ITERATIONS,
                   "salt": b64(salt), "iv": b64(iv), "data": b64(ct), "ids": sorted(notes)}, fh)
    print(f"encrypted {len(notes)} notes -> data/notes_private.enc.json")


def decrypt():
    with open(BUNDLE, encoding="utf-8") as fh:
        b = json.load(fh)
    d = lambda s: base64.b64decode(s)
    notes = json.loads(AESGCM(key(d(b["salt"]))).decrypt(d(b["iv"]), d(b["data"]), None))
    os.makedirs(PLAIN, exist_ok=True)
    for nid, text in notes.items():
        with open(os.path.join(PLAIN, nid + ".md"), "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"decrypted {len(notes)} notes -> data/private/notes/")


if __name__ == "__main__":
    {"encrypt": encrypt, "decrypt": decrypt}[sys.argv[1] if len(sys.argv) > 1 else "encrypt"]()
