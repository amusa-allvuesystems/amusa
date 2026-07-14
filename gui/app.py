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
from gui.rto_tracker import merge_attendance_into_rto_template, rows_to_csv  # noqa: E402

SAMPLE_HTML_PATH = ROOT / "sample_data" / "whos_been_in_today.html"
DEFAULT_RTO_TEMPLATE_PATH = ROOT / "sample_data" / "rto_tracker_london_2025.csv"


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
    st.caption(
        "Upload a Net2 Access Control HTML export, then generate an updated "
        "**RTO Tracker London - 2025 (Automation)** spreadsheet."
    )

    uploaded_file = st.file_uploader(
        "Upload Net2 HTML report",
        type=["html", "htm"],
        help="Export from Net2 Access Control: Who's been in today.",
    )

    rto_template_file = st.file_uploader(
        "RTO Tracker template (optional)",
        type=["csv"],
        help="Defaults to the bundled London 2025 automation template if not provided.",
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

    st.divider()
    st.subheader("RTO Tracker export")

    template_source: str | Path
    if rto_template_file is not None:
        template_source = rto_template_file.getvalue().decode("utf-8-sig", errors="replace")
    elif DEFAULT_RTO_TEMPLATE_PATH.is_file():
        template_source = DEFAULT_RTO_TEMPLATE_PATH
    else:
        st.warning("Upload your RTO Tracker automation CSV template to generate the export.")
        template_source = ""

    if template_source:
        try:
            rto_result = merge_attendance_into_rto_template(template_source, report)
        except Exception as exc:  # noqa: BLE001 - surface merge errors in the UI
            st.error(f"Could not update the RTO Tracker template: {exc}")
            return

        st.metric("Matched in RTO roster", rto_result.present_count)

        st.write(
            f"**{rto_result.attendee_count}** door entries applied to Step 1. "
            f"**{rto_result.present_count}** roster rows marked present (column G). "
            f"**{rto_result.roster_count}** people in the tracker."
        )

        if rto_result.unmatched_attendees:
            st.info(
                "These attendees were not found in the RTO roster: "
                + ", ".join(rto_result.unmatched_attendees)
            )

        rto_csv = rows_to_csv(rto_result.rows)
        date_suffix = report.report_date.replace(" ", "_") if report.report_date else "today"
        st.download_button(
            "Download RTO Tracker CSV",
            data=rto_csv,
            file_name=f"RTO_Tracker_London_2025_Automation_{date_suffix}.csv",
            mime="text/csv",
            type="primary",
        )

        st.caption(
            "Open the downloaded CSV in Excel or Google Sheets, or paste into your "
            "RTO Tracker London - 2025 (Automation) workbook. Step 1 door data is in "
            "columns A/C/D; Step 2 present flags are in column G."
        )

    csv_buffer = io.StringIO()
    filtered.to_csv(csv_buffer, index=False)
    st.download_button(
        "Download raw attendance CSV",
        data=csv_buffer.getvalue(),
        file_name="whos_been_in_today.csv",
        mime="text/csv",
    )

    if report.generated_at:
        st.caption(f"Net2 Access Control {report.generated_at}")


if __name__ == "__main__":
    main()
