#!/usr/bin/env python3
"""Local CLI for immutable ID tools (no Streamlit)."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gui.objectguid import (  # noqa: E402
    convert_objectguid,
    detect_objectguid_column,
)

USER_COLUMN_CANDIDATES = (
    "userprincipalname",
    "user_principal_name",
    "upn",
    "email",
    "mail",
    "user",
    "username",
)


def detect_user_column(columns: list[str]) -> str:
    normalized = {col: col.strip().lower() for col in columns}
    for candidate in USER_COLUMN_CANDIDATES:
        for column, name in normalized.items():
            if name == candidate:
                return column
    return columns[0]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"CSV is empty: {path}")
        rows = [{k: (v or "").strip() for k, v in row.items()} for row in reader]
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def cmd_convert(args: argparse.Namespace) -> int:
    if args.guid:
        result = convert_objectguid(args.guid)
        if not result.success:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1
        print(result.immutable_id)
        return 0

    if not args.input:
        raise SystemExit("Provide --input users.csv or --guid <object-guid>")

    input_path = Path(args.input)
    columns, rows = read_csv(input_path)
    guid_column = args.column or detect_objectguid_column(columns)

    output_rows: list[dict[str, str]] = []
    errors = 0
    for row in rows:
        value = row.get(guid_column, "").strip()
        result = convert_objectguid(value)
        out = dict(row)
        out["Immutable ID"] = result.immutable_id or ""
        out["Status"] = "OK" if result.success else "Error"
        out["Error"] = result.error or ""
        if not result.success:
            errors += 1
        output_rows.append(out)

    out_columns = columns + [c for c in ("Immutable ID", "Status", "Error") if c not in columns]
    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + "_immutable_ids.csv"
    )
    write_csv(output_path, out_columns, output_rows)

    print(f"Wrote {len(output_rows)} row(s) to {output_path}")
    if errors:
        print(f"{errors} error(s)", file=sys.stderr)
        return 1
    return 0


def ensure_az_login() -> None:
    result = subprocess.run(
        ["az", "account", "show"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit("Not logged in. Run: az login")


def lookup_user(user_id: str) -> dict:
    encoded = user_id.replace("@", "%40")
    result = subprocess.run(
        [
            "az", "rest",
            "--method", "GET",
            "--url",
            f"https://graph.microsoft.com/v1.0/users/{encoded}"
            "?$select=displayName,userPrincipalName,onPremisesImmutableId",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        return {"error": detail}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stdout.strip() or "Invalid response from Graph API"}


def cmd_lookup(args: argparse.Namespace) -> int:
    ensure_az_login()

    if args.user:
        payload = lookup_user(args.user)
        if "error" in payload:
            print(f"Error: {payload['error']}", file=sys.stderr)
            return 1
        print(json.dumps(payload, indent=2))
        return 0

    if not args.input:
        raise SystemExit("Provide --input users.csv or --user user@example.com")

    input_path = Path(args.input)
    columns, rows = read_csv(input_path)
    user_column = args.column or detect_user_column(columns)

    output_rows: list[dict[str, str]] = []
    errors = 0
    for row in rows:
        user_id = row.get(user_column, "").strip()
        if not user_id:
            continue
        payload = lookup_user(user_id)
        out = dict(row)
        if "error" in payload:
            out["Immutable ID"] = ""
            out["Status"] = "Error"
            out["Error"] = payload["error"]
            errors += 1
        else:
            out["Display Name"] = payload.get("displayName", "")
            out["User Principal Name"] = payload.get("userPrincipalName", "")
            out["Immutable ID"] = payload.get("onPremisesImmutableId") or ""
            out["Status"] = "OK"
            out["Error"] = ""
        output_rows.append(out)

    out_columns = columns + [
        c for c in ("Display Name", "User Principal Name", "Immutable ID", "Status", "Error")
        if c not in columns
    ]
    output_path = Path(args.output) if args.output else input_path.with_name(
        input_path.stem + "_immutable_ids.csv"
    )
    write_csv(output_path, out_columns, output_rows)

    print(f"Wrote {len(output_rows)} row(s) to {output_path}")
    if errors:
        print(f"{errors} error(s)", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Immutable ID tools for local use (no Streamlit).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser(
        "convert",
        help="Convert AD ObjectGUID to immutable ID (no Azure login needed)",
    )
    convert.add_argument("--input", "-i", help="Input CSV with ObjectGUID column")
    convert.add_argument("--output", "-o", help="Output CSV path")
    convert.add_argument("--column", "-c", help="ObjectGUID column name")
    convert.add_argument("--guid", "-g", help="Convert a single ObjectGUID")
    convert.set_defaults(func=cmd_convert)

    lookup = sub.add_parser(
        "lookup",
        help="Fetch immutable ID from Entra via az login",
    )
    lookup.add_argument("--input", "-i", help="Input CSV with email/UPN column")
    lookup.add_argument("--output", "-o", help="Output CSV path")
    lookup.add_argument("--column", "-c", help="User identifier column name")
    lookup.add_argument("--user", "-u", help="Look up a single user")
    lookup.set_defaults(func=cmd_lookup)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
