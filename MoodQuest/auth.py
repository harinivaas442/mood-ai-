"""Simple local accounts: email + password (salted PBKDF2 hashes, never plain text).

The FIRST account created becomes the developer/admin account (it can open Developer mode).
Google sign-in users are added through get_or_create_google_user().
No Streamlit imports here, so this file is easy to test.
"""
import hashlib
import hmac
import json
import os
import re
import secrets

USERS_PATH = "users.json"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ITERATIONS = 200_000


def _load(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(users, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def _public(email, rec):
    return {"email": email, "name": rec.get("name") or email.split("@")[0],
            "is_dev": bool(rec.get("is_dev"))}


def register(email, password, name="", path=USERS_PATH):
    """Create an account. Returns (ok, message, user_or_None)."""
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return False, "Please enter a valid email address.", None
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters.", None
    users = _load(path)
    if email in users:
        return False, "That email already has an account. Try signing in.", None
    salt = secrets.token_bytes(16)
    users[email] = {"name": name.strip(), "salt": salt.hex(), "hash": _hash(password, salt),
                    "is_dev": len(users) == 0, "provider": "password"}
    _save(users, path)
    return True, "Account created!", _public(email, users[email])


def login(email, password, path=USERS_PATH):
    """Check email + password. Returns (ok, message, user_or_None)."""
    email = (email or "").strip().lower()
    users = _load(path)
    rec = users.get(email)
    if not rec or "hash" not in rec:
        return False, "Wrong email or password.", None
    expected = rec["hash"]
    actual = _hash(password or "", bytes.fromhex(rec["salt"]))
    if not hmac.compare_digest(expected, actual):
        return False, "Wrong email or password.", None
    return True, "Welcome back!", _public(email, rec)


def get_or_create_google_user(email, name="", path=USERS_PATH):
    """Called after a successful Google sign-in."""
    email = (email or "").strip().lower()
    users = _load(path)
    if email not in users:
        users[email] = {"name": name, "is_dev": len(users) == 0, "provider": "google"}
        _save(users, path)
    return _public(email, users[email])


def list_users(path=USERS_PATH):
    """[(email, is_dev, provider)] for every account (no passwords)."""
    return [(e, bool(r.get("is_dev")), r.get("provider", "password")) for e, r in _load(path).items()]


def set_developer(email, path=USERS_PATH, exclusive=True):
    """Make `email` the developer. exclusive=True removes developer rights from everyone else."""
    email = (email or "").strip().lower()
    users = _load(path)
    if email not in users:
        return False
    for e, rec in users.items():
        if e == email:
            rec["is_dev"] = True
        elif exclusive:
            rec["is_dev"] = False
    _save(users, path)
    return True
