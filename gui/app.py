"""Streamlit GUI for batch Entra ID immutable ID lookups from CSV."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.azure_graph import fetch_immutable_ids, get_graph_token  # noqa: E402
from gui.secrets import (  # noqa: E402
    SECRETS_TEMPLATE,
    apply_streamlit_secrets,
    default_auth_mode,
    hosted_platform_name,
    resolve_auth_mode,
    secrets_status_message,
    service_principal_configured,
    use_managed_auth_ui,
)

USER_COLUMN_CANDIDATES = (
    "userprincipalname",
    "user_principal_name",
    "upn",
    "email",
    "mail",
    "user",
    "username",
    "user id",
    "userid",
    "objectid",
    "object_id",
)


def detect_user_column(columns: list[str]) -> str | None:
    normalized = {column: column.strip().lower() for column in columns}
    for candidate in USER_COLUMN_CANDIDATES:
        for column, column_name in normalized.items():
            if column_name == candidate:
                return column
    return columns[0] if columns else None


def results_to_dataframe(results) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Input": result.user_identifier,
                "Display Name": result.display_name,
                "User Principal Name": result.user_principal_name,
                "Immutable ID": result.on_premises_immutable_id,
                "Status": "OK" if result.success else "Error",
                "Error": result.error or "",
            }
            for result in results
        ]
    )


def main() -> None:
    apply_streamlit_secrets()

    st.set_page_config(
        page_title="Entra Immutable ID Lookup",
        page_icon="🔐",
        layout="wide",
    )

    st.title("Entra Immutable ID Lookup")
    st.caption("Upload a CSV of users and fetch onPremisesImmutableId values from Microsoft Entra ID.")

    with st.sidebar:
        st.header("Authentication")
        if use_managed_auth_ui():
            platform = hosted_platform_name() or "Streamlit Cloud"
            if service_principal_configured():
                st.success(f"Using Azure app registration ({platform})")
                auth_mode = "service_principal"
            else:
                st.error("Azure credentials not loaded yet.")
                st.markdown(
                    "In Streamlit Cloud go to **Manage app → Settings → Secrets**, "
                    "paste this, save, then **Reboot app**:"
                )
                st.code(SECRETS_TEMPLATE, language="toml")
                auth_mode = "service_principal"
        else:
            auth_mode = st.radio(
                "Sign-in method",
                options=["service_principal", "browser", "default"],
                index=["service_principal", "browser", "default"].index(default_auth_mode()),
                format_func=lambda value: {
                    "default": "Azure CLI (run az login first)",
                    "browser": "Interactive browser login",
                    "service_principal": "App registration (recommended)",
                }[value],
            )

            if auth_mode == "service_principal":
                st.info(
                    "Set credentials in `.streamlit/secrets.toml` locally, or in "
                    "Streamlit Cloud → Settings → Secrets."
                )

        st.caption(secrets_status_message())

        st.divider()
        st.markdown(
            """
**Required Graph permission**

- Delegated: `User.Read.All`
- Application: `User.Read.All` (service principal)
            """
        )

    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        help="CSV should include a column with user email, UPN, or object ID.",
    )

    sample_csv = """userPrincipalName
amusa@allvuesystems.com
jane.doe@example.com
"""
    with st.expander("Example CSV format"):
        st.code(sample_csv.strip(), language="csv")
        st.download_button(
            "Download sample CSV",
            data=sample_csv,
            file_name="sample_users.csv",
            mime="text/csv",
        )

    manual_entries = st.text_area(
        "Or paste user identifiers (one per line)",
        placeholder="user@example.com\nanother.user@example.com",
    )

    if uploaded_file is None and not manual_entries.strip():
        st.info("Upload a CSV file or paste user identifiers to begin.")
        return

    if uploaded_file is not None:
        dataframe = pd.read_csv(uploaded_file)
        if dataframe.empty:
            st.error("The uploaded CSV has no rows.")
            return

        st.subheader("Preview")
        st.dataframe(dataframe.head(20), use_container_width=True)

        user_column = st.selectbox(
            "User identifier column",
            options=list(dataframe.columns),
            index=list(dataframe.columns).index(detect_user_column(list(dataframe.columns))),
        )
        user_identifiers = (
            dataframe[user_column].dropna().astype(str).str.strip().replace("", pd.NA).dropna().tolist()
        )
    else:
        user_identifiers = [
            line.strip() for line in manual_entries.splitlines() if line.strip()
        ]
        user_column = "manual_input"

    st.write(f"**{len(user_identifiers)}** user(s) ready to look up.")

    secrets_ready = service_principal_configured() or not use_managed_auth_ui()
    if use_managed_auth_ui() and not service_principal_configured():
        st.warning("Add Azure secrets in Streamlit Cloud, reboot the app, then try again.")

    if st.button(
        "Fetch immutable IDs",
        type="primary",
        disabled=not user_identifiers or not secrets_ready,
    ):
        with st.spinner("Authenticating and querying Microsoft Graph..."):
            try:
                effective_auth_mode = resolve_auth_mode(auth_mode)
                token = get_graph_token(effective_auth_mode)
                results = fetch_immutable_ids(token, user_identifiers)
            except Exception as exc:  # noqa: BLE001 - surface auth errors in the UI
                st.error(f"Authentication failed: {exc}")
                return

        output = results_to_dataframe(results)
        success_count = sum(1 for result in results if result.success)
        error_count = len(results) - success_count

        st.subheader("Results")
        metric_cols = st.columns(3)
        metric_cols[0].metric("Processed", len(results))
        metric_cols[1].metric("Succeeded", success_count)
        metric_cols[2].metric("Errors", error_count)

        st.dataframe(output, use_container_width=True)

        csv_buffer = io.StringIO()
        output.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download results CSV",
            data=csv_buffer.getvalue(),
            file_name="immutable_id_results.csv",
            mime="text/csv",
        )

        if uploaded_file is not None:
            merged = dataframe.copy()
            result_map = {
                result.user_identifier: result.on_premises_immutable_id for result in results if result.success
            }
            error_map = {result.user_identifier: result.error for result in results if not result.success}
            merged["Immutable ID"] = merged[user_column].map(result_map)
            merged["Lookup Error"] = merged[user_column].map(error_map).fillna("")

            merged_buffer = io.StringIO()
            merged.to_csv(merged_buffer, index=False)
            st.download_button(
                "Download merged CSV",
                data=merged_buffer.getvalue(),
                file_name="users_with_immutable_ids.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
