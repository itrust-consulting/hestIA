#!/usr/bin/env python3
import os
import re
import json
import argparse
from pathlib import Path
from time import time
from datetime import datetime, timedelta, timezone

from hestia.utils.user_db import create_sqlite_connection, UserRepository
from hestia.services.users import UserService


RELATIVE_RE = re.compile(r"^\+(\d+)([smhdw])$")

def now_epoch() -> int:
    return int(time() * 1000)

def parse_datetime(value: str | None) -> int | None:
    """
    Parse ISO8601, date-only, 'now', 'never', or relative (+7d) inputs.
    Returns epoch milliseconds or None.
    """
    if not value or value.lower() == "never":
        return None

    v = value.strip().lower()
    if v == "now":
        return now_epoch()

    # Relative: +7d, +3h, ...
    m = RELATIVE_RE.match(v)
    if m:
        amount, unit = m.groups()
        amount = int(amount)
        delta = {
            "s": timedelta(seconds=amount),
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
        }[unit]
        return int((datetime.now(timezone.utc) + delta).timestamp() * 1000)

    # ISO or date
    try:
        if "t" in v:
            dt = datetime.fromisoformat(v.replace("z", "+00:00"))
        else:
            dt = datetime.fromisoformat(v).replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        raise SystemExit(f"Invalid datetime format: {value}")

def validate_db_path(path_str: str) -> Path:
    path = Path(path_str)

    if not path.parent.exists():
        raise SystemExit(f"Error: Directory does not exist: {path.parent}")

    if not path.parent.is_dir():
        raise SystemExit(f"Error: {path.parent} is not a directory.")

    if path.exists():
        if path.is_dir():
            raise SystemExit(f"Error: {path} is a directory.")
        if not os.access(path, os.R_OK):
            raise SystemExit(f"Error: No read permission for {path}")
        if not os.access(path, os.W_OK):
            raise SystemExit(f"Error: No write permission for {path}")
    else:
        try:
            path.touch(exist_ok=True)
        except Exception as e:
            raise SystemExit(f"Cannot create DB file: {e}")

    return path

def create_user_from_dict(u: dict, svc: UserService):
    required = {"username", "email", "password", "role", "first_name", "last_name"}
    missing = required - set(u.keys())
    if missing:
        raise SystemExit(f"User missing fields: {', '.join(missing)}")

    expires_ts = parse_datetime(u.get("expires_at"))

    svc.create_user(
        username=u["username"],
        email=u["email"],
        password=u["password"],
        first_name=u["first_name"],
        last_name=u["last_name"],
        role=u["role"],
        expires_at=expires_ts,
    )

    print(f"Created user '{u['username']}' (role={u['role']})")


def validate_single_user_args(args):
    missing = []
    for field in ["name", "email", "pw", "role", "first", "last"]:
        if not getattr(args, field):
            missing.append(f"--{field}")
    if missing:
        raise SystemExit("Missing required fields: " + ", ".join(missing))

def handle_add_user(args, svc: UserService):
    if args.from_json:
        users = json.load(open(args.from_json, "r", encoding="utf-8"))
        if not isinstance(users, list):
            raise SystemExit("JSON must contain a list")
        for u in users:
            create_user_from_dict(u, svc)
    else:
        validate_single_user_args(args)
        create_user_from_dict(
            {
                "username": args.name,
                "email": args.email,
                "password": args.pw,
                "role": args.role,
                "first_name": args.first,
                "last_name": args.last,
                "expires_at": args.expires_at,
            },
            svc,
        )

def resolve_user_for_deletion(args, svc: UserService):
    if args.name:
        return svc.repo.get_user_by_username(args.name)
    if args.email:
        return svc.repo.get_user_by_email(args.email)
    if args.id:
        try:
            uid = bytes.fromhex(args.id)
        except ValueError:
            raise SystemExit("Invalid hex ID")
        return svc.repo.get_user_by_id(uid)

    raise SystemExit("Provide --name, --email, or --id")

def handle_delete_user(args, svc: UserService):
    row = resolve_user_for_deletion(args, svc)
    if not row:
        raise SystemExit("User not found")

    user_id = row["id"]
    username = row["username"]

    confirm = input(f"Delete user '{username}'? [y/N]: ").lower().strip()
    if confirm != "y":
        print("Aborted.")
        return

    svc.delete_user(user_id)
    print(f"Deleted '{username}'")

def handle_list_users(svc: UserService):
    rows = svc.list_users()
    if not rows:
        print("No users.")
        return

    print(
        f"{'ID':36} {'Username':15} {'Email':25} {'MustChange':12} "
        f"{'Created':12} {'Updated':12} {'Expires'}"
    )
    print("-" * 130)

    for r in rows:
        created = datetime.fromtimestamp(r["created_at"] / 1000).strftime("%Y-%m-%d")
        updated = datetime.fromtimestamp(r["updated_at"] / 1000).strftime("%Y-%m-%d")
        expires = (
            "never"
            if r["expires_at"] is None
            else datetime.fromtimestamp(r["expires_at"] / 1000).strftime("%Y-%m-%d")
        )
        mc = "yes" if r["must_change_pw"] else "no"

        print(
            f"{r['id']:36} {r['username']:15} {r['email']:25} {mc:12} "
            f"{created:12} {updated:12} {expires}"
        )

def handle_list_orgs(svc: UserService):
    rows = svc.list_orgs()
    if not rows:
        print("No organizations.")
        return

    print(f"{'ID':4} {'Name':25} {'Abbr':8} {'Created'}")
    print("-" * 60)

    for org in rows:
        ts = org["created_at"]
        if ts > 10_000_000_000:
            ts /= 1000
        created = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        print(f"{org['id']:4} {org['name']:25} {org['abbreviation']:8} {created}")

def handle_create_org(args, svc: UserService):
    svc.create_org(args.name, args.abbr)
    print(f"Created org '{args.name}'")

def handle_delete_org(args, svc: UserService):
    svc.delete_org(args.id)
    print(f"Deleted org {args.id}")

def handle_update_org(args, svc: UserService):
    svc.update_org(args.id, args.name, args.abbr)
    print(f"Updated org {args.id}")

def handle_list_org_users(args, svc: UserService):
    rows = svc.list_org_users(args.id)
    if not rows:
        print("No users.")
        return

    print(f"{'ID':36} {'Username':20} {'Email':25}")
    print("-" * 90)
    for r in rows:
        print(f"{r['id']:36} {r['username']:20} {r['email']:25}")

def handle_list_roles(svc: UserService):
    rows = svc.list_roles()
    print(f"{'ID':4} {'Name':20} {'Description'}")
    print("-" * 60)
    for r in rows:
        print(f"{r['id']:4} {r['name']:20} {r['description']}")

def handle_assign_role(args, svc: UserService):
    user = svc.repo.get_user_by_username(args.user)
    if not user:
        raise SystemExit("User not found")

    svc.assign_role_to_user(user["id"], args.role)
    print(f"Assigned '{args.role}' to {args.user}")

def handle_revoke_role(args, svc: UserService):
    user = svc.repo.get_user_by_username(args.user)
    if not user:
        raise SystemExit("User not found")

    # args.role here is a role *name*, svc.revoke expects ID — fix:
    role = svc.repo.get_role_by_name(args.role)
    if not role:
        raise SystemExit("Role not found")

    svc.revoke_role_from_user(user["id"], role["id"])
    print(f"Revoked '{args.role}' from {args.user}")

def handle_list_user_roles(args, svc: UserService):
    user = svc.repo.get_user_by_username(args.user)
    if not user:
        raise SystemExit("User not found")

    print(json.dumps(svc.list_user_roles(user["id"]), indent=2))

def handle_list_permissions(svc: UserService):
    rows = svc.list_permissions()
    print(f"{'ID':4} {'Name':20} {'Description'}")
    print("-" * 80)
    for r in rows:
        print(f"{r['id']:4} {r['name']:20} {r['description']}")

def handle_list_user_permissions(args, svc: UserService):
    user = svc.repo.get_user_by_username(args.user)
    if not user:
        raise SystemExit("User not found")

    perms = svc.permissions.compute_user_permissions(user["id"])
    print(json.dumps(perms, indent=2))

def handle_set_user_permission(args, svc: UserService):
    user = svc.repo.get_user_by_username(args.user)
    if not user:
        raise SystemExit("User not found")

    starts = parse_datetime(args.starts)
    expires = parse_datetime(args.expires)

    perm = svc.repo.get_permission_by_name(args.permission)
    if not perm:
        raise SystemExit("Permission not found")

    svc.set_user_permission(
        user_id=user["id"],
        permission_id=perm["id"],
        value=args.value,
        starts_ts=starts,
        expires_ts=expires,
    )

    print(f"Set permission override: {args.permission}={args.value}")

def handle_init_db(args, svc: UserService):
    with open(args.from_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # -----------------------------
    # Roles
    # -----------------------------
    for r in data.get("roles", []):
        svc.repo.insert_role(
            name=r["name"],
            description=r.get("description", "")
        )

    # -----------------------------
    # Permissions
    # -----------------------------
    for p in data.get("permissions", []):
        svc.repo.insert_permission(
            name=p["name"],
            description=p.get("description", "")
        )

    # -----------------------------
    # Role → Permission assignments
    # -----------------------------
    for rp in data.get("role_permissions", []):
        role = svc.repo.get_role_by_name(rp["role"])
        if not role:
            raise SystemExit(f"Role not found: {rp['role']}")

        perm = svc.repo.get_permission_by_name(rp["permission"])
        if not perm:
            raise SystemExit(f"Permission not found: {rp['permission']}")

        svc.repo.set_role_permission(
            role_id=role["id"],
            permission_id=perm["id"],
            value=rp.get("value")
        )

    # -----------------------------
    # Organizations
    # -----------------------------
    for org in data.get("organizations", []):
        svc.create_org(
            name=org["name"],
            abbreviation=org["abbreviation"]
        )

    # -----------------------------
    # Users
    # -----------------------------
    for u in data.get("users", []):
        expires_ts = parse_datetime(u.get("expires_at"))

        user_id = svc.create_user(
            username=u["username"],
            email=u["email"],
            password=u["password"],
            first_name=u["first_name"],
            last_name=u["last_name"],
            role=u["role"],
            expires_at=expires_ts
        )

        # Add user to first matching org
        org_name = u.get("organization")
        if org_name:
            org = svc.repo.get_organization_by_name(org_name)
            if not org:
                raise SystemExit(f"Organization not found: {org_name}")
            svc.add_user_to_org(user_id, org["id"])

        # User-specific overrides
        overrides = u.get("override_permissions", {})
        for perm_name, value in overrides.items():
            perm = svc.repo.get_permission_by_name(perm_name)
            if not perm:
                raise SystemExit(f"Permission not found: {perm_name}")

            svc.set_user_permission(
                user_id=user_id,
                permission_id=perm["id"],
                value=json.dumps(value),
                starts_ts=now_epoch(),
                expires_ts=None
            )

    print("Database initialized successfully.")

def parse_args():
    parser = argparse.ArgumentParser(
        prog="hestia-db",
        description="Manage the hestIA user database."
    )

    parser.add_argument("-p", "--path", required=True)

    sub = parser.add_subparsers(dest="command", required=True)

    # Add user
    a = sub.add_parser("add-user")
    a.add_argument("--from-json")
    a.add_argument("-n", "--name")
    a.add_argument("-e", "--email")
    a.add_argument("--pw")
    a.add_argument("--role")
    a.add_argument("--first")
    a.add_argument("--last")
    a.add_argument("--expires-at")

    # Delete user
    d = sub.add_parser("delete-user")
    d.add_argument("--name")
    d.add_argument("--email")
    d.add_argument("--id")

    sub.add_parser("list-users")

    # Orgs
    sub.add_parser("list-orgs")

    co = sub.add_parser("create-org")
    co.add_argument("--name", required=True)
    co.add_argument("--abbr", required=True)

    do = sub.add_parser("delete-org")
    do.add_argument("--id", required=True, type=int)

    uo = sub.add_parser("update-org")
    uo.add_argument("--id", required=True, type=int)
    uo.add_argument("--name", required=True)
    uo.add_argument("--abbr", required=True)

    lou = sub.add_parser("list-org-users")
    lou.add_argument("--id", required=True, type=int)

    # Roles
    sub.add_parser("list-roles")

    ar = sub.add_parser("assign-role")
    ar.add_argument("--user", required=True)
    ar.add_argument("--role", required=True)

    rr = sub.add_parser("revoke-role")
    rr.add_argument("--user", required=True)
    rr.add_argument("--role", required=True)

    lur = sub.add_parser("list-user-roles")
    lur.add_argument("--user", required=True)

    # Permissions
    sub.add_parser("list-permissions")

    lup = sub.add_parser("list-user-permissions", help="List effective permissions for a user")
    lup.add_argument("--user", required=True)
    
    sp = sub.add_parser("set-user-permission")
    sp.add_argument("--user", required=True)
    sp.add_argument("--permission", required=True)
    sp.add_argument("--value", required=True)
    sp.add_argument("--starts", default="now")
    sp.add_argument("--expires", default="never")

    init_db = sub.add_parser("init-db", help="Initialize DB from JSON")
    init_db.add_argument("--from-json", required=True)

    return parser.parse_args()


def main():
    args = parse_args()
    db = validate_db_path(args.path)

    get_conn, close, lock = create_sqlite_connection(db)
    repo = UserRepository(get_conn, lock)
    svc = UserService(repo)

    repo.initialize()

    if args.command == "init-db":
        handle_init_db(args, svc)

    elif args.command == "add-user":
        handle_add_user(args, svc)

    elif args.command == "delete-user":
        handle_delete_user(args, svc)

    elif args.command == "list-users":
        handle_list_users(svc)

    elif args.command == "list-orgs":
        handle_list_orgs(svc)

    elif args.command == "create-org":
        handle_create_org(args, svc)

    elif args.command == "delete-org":
        handle_delete_org(args, svc)

    elif args.command == "update-org":
        handle_update_org(args, svc)

    elif args.command == "list-org-users":
        handle_list_org_users(args, svc)

    elif args.command == "list-roles":
        handle_list_roles(svc)

    elif args.command == "assign-role":
        handle_assign_role(args, svc)

    elif args.command == "revoke-role":
        handle_revoke_role(args, svc)

    elif args.command == "list-user-roles":
        handle_list_user_roles(args, svc)

    elif args.command == "list-permissions":
        handle_list_permissions(svc)

    elif args.command == "list-user-permissions":
        handle_list_user_permissions(args, svc)

    elif args.command == "set-user-permission":
        handle_set_user_permission(args, svc)

    close()

if __name__ == "__main__":
    main()