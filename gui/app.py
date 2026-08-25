"""Streamlit technology experience feedback form."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

SCALE_LABELS = {
    1: "Strongly disagree",
    2: "Disagree",
    3: "Neither agree nor disagree",
    4: "Agree",
    5: "Strongly agree",
}

EXPERIENCE_QUESTIONS = {
    "Meeting rooms": "Meeting rooms provide a consistent, reliable experience across the office.",
    "Collaboration tools": "Microsoft Teams and other collaboration tools work reliably when I need them.",
    "Hybrid working": "I have the technology and support I need to work effectively across office and remote locations.",
    "Executive & VIP support": "Technology support meets the needs of executives and other high-impact users.",
    "Service visibility": "I can easily understand the status and performance of the technology services I use.",
    "Proactive support": "Technology teams identify and resolve potential issues before they disrupt my work.",
    "Business value": "Technology services help me and my team deliver measurable business value.",
}


def init_session_state() -> None:
    """Set up in-browser response storage."""
    if "submissions" not in st.session_state:
        st.session_state.submissions = []


def score_label(score: int) -> str:
    """Return an accessible agreement-scale label."""
    return f"{score} — {SCALE_LABELS[score]}"


def render_scale_question(key: str, question: str) -> int:
    """Render one five-point agreement question."""
    return st.radio(
        question,
        options=range(1, 6),
        index=2,
        format_func=score_label,
        horizontal=True,
        key=key,
    )


def show_feedback_summary() -> None:
    """Show session-level response insights and a CSV export."""
    submissions = st.session_state.submissions
    if not submissions:
        return

    st.divider()
    st.subheader("Response snapshot")
    st.caption("Visible only for this browser session. Download responses to retain them.")
    responses = pd.DataFrame(submissions)
    question_columns = list(EXPERIENCE_QUESTIONS)
    averages = responses[question_columns].mean().sort_values()

    metrics = st.columns(3)
    metrics[0].metric("Responses", len(responses))
    metrics[1].metric("Overall experience", f"{averages.mean():.1f} / 5")
    metrics[2].metric("Lowest-scoring area", averages.index[0])

    st.bar_chart(averages.rename("Average rating").to_frame(), horizontal=True)
    st.download_button(
        "Download responses as CSV",
        data=responses.to_csv(index=False),
        file_name="technology_experience_feedback.csv",
        mime="text/csv",
    )


def main() -> None:
    """Render the feedback experience."""
    st.set_page_config(
        page_title="Technology Experience Feedback",
        page_icon="💬",
        layout="wide",
    )
    init_session_state()

    st.title("Technology experience feedback")
    st.markdown(
        "Help us prioritize improvements to workplace technology. This survey takes about **3 minutes**; "
        "please rate each statement based on your recent experience."
    )
    st.info(
        "Your responses are collected in this browser session only. "
        "Please download the CSV after collecting feedback."
    )

    with st.form("technology_feedback", clear_on_submit=True):
        st.subheader("About you")
        details = st.columns(2)
        with details[0]:
            role = st.selectbox(
                "Which best describes your role?",
                ["Individual contributor", "People manager", "Executive / VIP", "IT / technology", "Other"],
            )
        with details[1]:
            work_style = st.selectbox(
                "Where do you work most often?",
                ["Mostly in an office", "Hybrid", "Mostly remote", "Multiple office locations"],
            )

        st.subheader("Your experience")
        st.caption("1 = Strongly disagree · 3 = Neither agree nor disagree · 5 = Strongly agree")
        ratings = {
            section: render_scale_question(f"rating_{section}", question)
            for section, question in EXPERIENCE_QUESTIONS.items()
        }

        st.subheader("Help us focus")
        priorities = st.multiselect(
            "Which areas should we improve first? Select up to three.",
            options=list(EXPERIENCE_QUESTIONS),
            max_selections=3,
        )
        issue_description = st.text_area(
            "What is the most important technology issue we should solve?",
            placeholder="Describe what happens, where it occurs, and how it affects your work.",
        )
        success_looks_like = st.text_area(
            "What would a better experience look like for you?",
            placeholder="For example: reliable video meetings, faster issue resolution, or clearer service updates.",
        )
        follow_up = st.radio("May we contact you about your feedback?", ["No", "Yes"], horizontal=True)
        contact = st.text_input("Email or Teams handle (optional)") if follow_up == "Yes" else ""

        submitted = st.form_submit_button("Submit feedback", type="primary")

    if submitted:
        record = {
            "Submitted at (UTC)": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "Role": role,
            "Work style": work_style,
            **ratings,
            "Priority areas": "; ".join(priorities),
            "Most important issue": issue_description,
            "Better experience": success_looks_like,
            "Follow-up permitted": follow_up,
            "Contact": contact,
        }
        st.session_state.submissions.append(record)
        st.success("Thank you — your feedback has been recorded.")

    show_feedback_summary()


if __name__ == "__main__":
    main()
