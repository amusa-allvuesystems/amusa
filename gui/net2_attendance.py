"""Parse Net2 Access Control 'Who's been in today' HTML reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class AttendanceRecord:
    date: str
    department: str
    user_name: str


@dataclass(frozen=True)
class AttendanceReport:
    report_date: str | None
    generated_at: str | None
    records: list[AttendanceRecord]

    @property
    def total_count(self) -> int:
        return len(self.records)

    def department_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.department] = counts.get(record.department, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


class _Net2AttendanceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.report_date: str | None = None
        self.generated_at: str | None = None
        self.records: list[AttendanceRecord] = []
        self._in_h2 = False
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._is_header_row = False
        self._current_row: list[str] = []
        self._body_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "h2":
            self._in_h2 = True
        elif tag == "table":
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._current_row = []
            class_attr = dict(attrs).get("class", "")
            self._is_header_row = "head" in (class_attr or "")
        elif tag in {"td", "th"} and self._in_row:
            self._in_cell = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h2":
            self._in_h2 = False
        elif tag == "table":
            self._in_table = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if not self._is_header_row and len(self._current_row) == 3:
                date, department, user_name = self._current_row
                self.records.append(
                    AttendanceRecord(
                        date=date.strip(),
                        department=department.strip(),
                        user_name=user_name.strip(),
                    )
                )
            self._current_row = []
            self._is_header_row = False
        elif tag in {"td", "th"} and self._in_cell:
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return

        if self._in_h2 and self.report_date is None:
            match = re.search(r"on\s+(.+)$", text, re.IGNORECASE)
            self.report_date = match.group(1).strip() if match else text

        if self._in_cell:
            self._current_row.append(text)
        elif not self._in_table and not self._in_h2:
            self._body_text_parts.append(text)


def parse_attendance_html(html: str) -> AttendanceReport:
    """Parse a Net2 'Who's been in today' HTML export."""
    parser = _Net2AttendanceParser()
    parser.feed(html)

    body_text = " ".join(parser._body_text_parts)
    generated_match = re.search(
        r"Net2 Access Control\s+(.+)$",
        body_text,
        re.IGNORECASE,
    )
    generated_at = generated_match.group(1).strip() if generated_match else None

    return AttendanceReport(
        report_date=parser.report_date,
        generated_at=generated_at,
        records=parser.records,
    )
