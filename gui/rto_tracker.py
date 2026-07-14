"""Merge Net2 attendance into the RTO Tracker London automation spreadsheet."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gui.net2_attendance import AttendanceRecord, AttendanceReport

RTO_COLUMN_COUNT = 9
EXCLUDED_DEPARTMENTS = {"__External"}


@dataclass(frozen=True)
class RtoMergeResult:
    rows: list[list[str]]
    attendee_count: int
    present_count: int
    roster_count: int
    unmatched_attendees: list[str]


def normalize_person_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip())
    if "," in cleaned:
        last, first = cleaned.split(",", 1)
        return f"{last.strip().lower()}, {first.strip().lower()}"
    return cleaned.lower()


def surname_key(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip())
    if "," in cleaned:
        return cleaned.split(",", 1)[0].strip().lower()
    return cleaned.lower()


def extract_surname_label(name: str) -> str:
    """Format used in column A and I, e.g. 'Casey,'."""
    cleaned = re.sub(r"\s+", " ", name.strip())
    if "," in cleaned:
        surname = cleaned.split(",", 1)[0].strip()
    else:
        surname = cleaned
    return f"{surname}," if surname else ""


def clean_department(department: str) -> str:
    cleaned = department.strip().lstrip("_")
    return cleaned or department.strip()


def format_rto_date(date_value: str) -> str:
    value = date_value.strip()
    for fmt in ("%d/%m/%Y", "%d %B %Y", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(value, fmt)
            return f"{parsed.month}/{parsed.day}/{parsed.year}"
        except ValueError:
            continue
    return value


def resolve_report_date(report: AttendanceReport) -> str:
    if report.records:
        return format_rto_date(report.records[0].date)
    if report.report_date:
        return format_rto_date(report.report_date)
    return ""


def load_rto_template(source: str | Path) -> list[list[str]]:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8-sig")
    else:
        path = Path(source)
        text = path.read_text(encoding="utf-8-sig") if path.is_file() else source

    rows: list[list[str]] = []
    for row in csv.reader(io.StringIO(text)):
        padded = list(row) + [""] * (RTO_COLUMN_COUNT - len(row))
        rows.append(padded[:RTO_COLUMN_COUNT])
    return rows


def _is_total_row(row: list[str]) -> bool:
    return row[0].strip().lower().startswith("total")


def _data_row_indices(rows: list[list[str]]) -> list[int]:
    indices: list[int] = []
    for index, row in enumerate(rows):
        if index == 0 or _is_total_row(row):
            continue
        indices.append(index)
    return indices


def _door_paste_indices(rows: list[list[str]]) -> list[int]:
    """Rows with full names in column E (Step 1 paste area)."""
    indices: list[int] = []
    for index in _data_row_indices(rows):
        if rows[index][4].strip():
            indices.append(index)
        else:
            break
    return indices


def _surname_only_indices(rows: list[list[str]]) -> list[int]:
    """Rows with surname-only roster entries in column A."""
    indices: list[int] = []
    for index in _data_row_indices(rows):
        row = rows[index]
        if row[4].strip():
            continue
        if row[0].strip() and not row[2].strip() and not row[3].strip():
            indices.append(index)
    return indices


def _employee_attendees(report: AttendanceReport) -> list[AttendanceRecord]:
    return [record for record in report.records if record.department.strip() not in EXCLUDED_DEPARTMENTS]


def apply_attendance_to_rto(
    template_rows: list[list[str]],
    report: AttendanceReport,
) -> RtoMergeResult:
    rows = [list(row) for row in template_rows]
    door_indices = _door_paste_indices(rows)
    surname_indices = _surname_only_indices(rows)
    roster_indices = door_indices + surname_indices
    attendees = _employee_attendees(report)
    report_date = resolve_report_date(report)

    attendee_full_names = {normalize_person_name(record.user_name) for record in attendees}
    attendee_surnames = {surname_key(record.user_name) for record in attendees}
    roster_full_names = {normalize_person_name(rows[index][4]) for index in door_indices}

    for index in door_indices:
        rows[index][0] = ""
        rows[index][2] = ""
        rows[index][3] = ""

    for offset, index in enumerate(door_indices):
        if offset >= len(attendees):
            continue
        record = attendees[offset]
        rows[index][0] = extract_surname_label(record.user_name)
        rows[index][2] = report_date
        rows[index][3] = clean_department(record.department)

    present_count = 0
    for index in door_indices:
        roster_name = rows[index][4].strip()
        present = normalize_person_name(roster_name) in attendee_full_names
        rows[index][6] = "1" if present else "0"
        rows[index][8] = extract_surname_label(roster_name)
        if present:
            present_count += 1

    for index in surname_indices:
        roster_surname = surname_key(rows[index][0])
        present = roster_surname in attendee_surnames
        rows[index][6] = "1" if present else "0"
        if rows[index][8].strip() in {"", "#VALUE!"}:
            rows[index][8] = extract_surname_label(rows[index][0])
        if present:
            present_count += 1

    for index, row in enumerate(rows):
        if _is_total_row(row):
            rows[index][6] = str(present_count)

    unmatched_attendees = sorted(
        {
            record.user_name.strip()
            for record in attendees
            if normalize_person_name(record.user_name) not in roster_full_names
            and surname_key(record.user_name)
            not in {surname_key(rows[idx][0]) for idx in surname_indices}
        },
        key=str.casefold,
    )

    return RtoMergeResult(
        rows=rows,
        attendee_count=len(attendees),
        present_count=present_count,
        roster_count=len(roster_indices),
        unmatched_attendees=unmatched_attendees,
    )


def rows_to_csv(rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue()


def merge_attendance_into_rto_template(
    template_source: str | Path,
    report: AttendanceReport,
) -> RtoMergeResult:
    template_rows = load_rto_template(template_source)
    return apply_attendance_to_rto(template_rows, report)
