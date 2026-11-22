"""Account commands for the operator (the first admin, and recovery when locked out).

    python -m north.auth.cli create-user --username ana --role admin
    python -m north.auth.cli reset-password --username ana
    python -m north.auth.cli reset-totp --username ana
    python -m north.auth.cli list-users

Passwords are read from the terminal (never from arguments, which land in shell history), or
generated with --generate and shown once. Every account starts with "must change password".
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys

from sqlalchemy import select

from north.auth import audit, service
from north.auth.passwords import WeakPassword, check_policy, hash_password
from north.repository.db import get_sessionmaker
from north.repository.models import User

ACTOR = "cli"


def _password(username: str, generate: bool) -> str:
    if generate:
        pw = secrets.token_urlsafe(18)
        print(f"temporary password for {username} (shown once): {pw}", flush=True)
        return pw
    while True:
        pw = getpass.getpass("temporary password: ")
        try:
            check_policy(pw, username=username)
        except WeakPassword as e:
            print(f"refused: {e}", file=sys.stderr)
            continue
        if getpass.getpass("again: ") == pw:
            return pw
        print("the two entries differ", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="north.auth.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("create-user", "reset-password", "reset-totp", "enable", "disable"):
        p = sub.add_parser(name)
        p.add_argument("--username", required=True)
        if name == "create-user":
            p.add_argument("--role", choices=service.ROLES, default="admin")
        if name in ("create-user", "reset-password"):
            p.add_argument("--generate", action="store_true", help="generate and show a password")
    sub.add_parser("list-users")
    a = ap.parse_args(argv)

    with get_sessionmaker()() as db:
        if a.cmd == "list-users":
            for u in db.scalars(select(User).order_by(User.username)):
                state = "disabled" if u.disabled else "active"
                mfa = "totp" if u.totp_secret else "no-totp"
                print(f"{u.username:<24} {u.role:<8} {state:<8} {mfa:<8} "
                      f"last login {u.last_login_at}")
            return 0
        name = service.check_username(a.username)
        if a.cmd == "create-user":
            service.create_user(db, name, a.role, _password(name, a.generate), actor=ACTOR)
            print(f"created {name} ({a.role}); first login asks for a new password"
                  " and an authenticator app", flush=True)
            return 0
        user = db.scalar(select(User).where(User.username == name))
        if user is None:
            print(f"no user {name}", file=sys.stderr)
            return 1
        if a.cmd == "reset-password":
            user.password_hash = hash_password(_password(name, a.generate))
            user.must_change_password = True
        elif a.cmd == "reset-totp":
            user.totp_secret = user.totp_pending_secret = None
            user.totp_last_step = None
        else:
            user.disabled = a.cmd == "disable"
        service.revoke_all(db, user.id)
        audit.record(db, a.cmd.replace("-", "_"), actor=ACTOR, target=f"user:{name}")
        db.commit()
        print(f"{a.cmd}: {name} done; their sessions were ended", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
