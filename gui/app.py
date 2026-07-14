"""Streamlit home page: Net2 daily attendance reports."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.net2_attendance import parse_attendance_html  # noqa: E402

SAMPLE_HTML_PATH = ROOT / "sample_data" / "whos_been_in_today.html"


def load_sample_html() -> str | None:
    if SAMPLE_HTML_PATH.is_file():
        return SAMPLE_HTML_PATH.read_text(encoding="utf-8")
    return None


def records_to_dataframe(report) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": record.date,
                "Department": record.department,
                "User name": record.user_name,
            }
            for record in report.records
        ]
    )


def main() -> None:
    st.set_page_config(
        page_title="Daily Attendance",
        page_icon="🏢",
        layout="wide",
    )

    st.title("Who's been in today")
    st.caption("Upload a Net2 Access Control HTML export to view daily building attendance.")

    uploaded_file = st.file_uploader(
        "Upload Net2 HTML report",
        type=["html", "htm"],
        help="Export from Net2 Access Control: Who's been in today.",
    )

    use_sample = st.checkbox("Load sample report (13 July 2026)", value=uploaded_file is None)

    html_content: str | None = None
    if uploaded_file is not None:
        html_content = uploaded_file.read().decode("utf-8", errors="replace")
    elif use_sample:
        html_content = load_sample_html()
        if html_content is None:
            st.warning("Sample report file is not available in this deployment.")

    if html_content is None:
        st.info("Upload a Net2 HTML report or enable the sample report to begin.")
        return

    try:
        report = parse_attendance_html(html_content)
    except Exception as exc:  # noqa: BLE001 - surface parse errors in the UI
        st.error(f"Could not parse the HTML report: {exc}")
        return

    if not report.records:
        st.warning("No attendance records found in this report.")
        return

    title_parts = ["Who's been in today"]
    if report.report_date:
        title_parts.append(f"on {report.report_date}")
    st.subheader(" ".join(title_parts))

    metric_cols = st.columns(3)
    metric_cols[0].metric("People in today", report.total_count)
    metric_cols[1].metric("Departments", len(report.department_counts()))
    if report.generated_at:
        metric_cols[2].metric("Report generated", report.generated_at)
    else:
        metric_cols[2].metric("Report generated", "—")

    dataframe = records_to_dataframe(report)

    department_filter = st.multiselect(
        "Filter by department",
        options=sorted(dataframe["Department"].unique()),
        default=[],
        placeholder="All departments",
    )

    filtered = dataframe
    if department_filter:
        filtered = dataframe[dataframe["Department"].isin(department_filter)]

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    with st.expander("By department"):
        dept_df = pd.DataFrame(
            [
                {"Department": department, "Count": count}
                for department, count in report.department_counts().items()
            ]
        )
        st.dataframe(dept_df, use_container_width=True, hide_index=True)

    csv_buffer = io.StringIO()
    filtered.to_csv(csv_buffer, index=False)
    st.download_button(
        "Download as CSV",
        data=csv_buffer.getvalue(),
        file_name="whos_been_in_today.csv",
        mime="text/csv",
    )

    if report.generated_at:
        st.caption(f"Net2 Access Control {report.generated_at}")


if __name__ == "__main__":
    main()
