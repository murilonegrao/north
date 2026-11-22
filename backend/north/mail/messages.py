"""Plain-text templates (locales/<code>.json), rendered when a message is queued.

Plain text only: no HTML, no remote images, no tracking. It is what an admin notice needs and
what spam filters trust most.
"""

from __future__ import annotations

import datetime as dt
import json
from functools import cache
from pathlib import Path
from typing import Any

LOCALES = ("en", "pt-BR")
_DIR = Path(__file__).parent / "locales"

# Messages about account security: always sent, with the security footer.
SECURITY = frozenset({"verify_email", "password_reset", "password_changed", "totp_changed",
                      "email_changed", "new_sign_in", "login_locked", "access_changed"})
# Messages that carry a live single-use link: the body is blanked once sent.
SENSITIVE = frozenset({"verify_email", "password_reset"})


@cache
def catalog(locale: str) -> dict[str, Any]:
    code = locale if locale in LOCALES else "en"
    return json.loads((_DIR / f"{code}.json").read_text(encoding="utf-8"))


def kinds() -> list[str]:
    return sorted(catalog("en")["messages"])


def when(t: dt.datetime | None = None) -> str:
    t = (t or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    return t.strftime("%Y-%m-%d %H:%M UTC")


def phrase(locale: str, group: str, key: str, **values: Any) -> str:
    """A short localized phrase (change descriptions, job statuses)."""
    text = catalog(locale)[group].get(key) or catalog("en")[group].get(key) or key
    return text.format(**values)


def render(kind: str, locale: str, *, public_url: str, **values: Any) -> tuple[str, str]:
    """(subject, body) for a message kind. Missing placeholders raise KeyError."""
    cat = catalog(locale)
    tpl = cat["messages"].get(kind) or catalog("en")["messages"][kind]
    admin_url = public_url.rstrip("/") + "/admin"
    values = {"admin_url": admin_url, "account_url": admin_url + "/account", "at": when(),
              **values}
    subject = tpl["subject"].format(**values)
    footer_key = "security" if kind in SECURITY else ("jobs" if kind == "job_failed" else "plain")
    tail = [cat["signature"].format(**values), cat["footer"][footer_key].format(**values)]
    body = tpl["body"].format(**values) + "\n\n-- \n" + "\n".join(filter(None, tail)) + "\n"
    # A subject is one header line.
    return " ".join(subject.split()), body
