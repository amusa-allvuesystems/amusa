"""Streamlit GUI for immutable ID tools."""

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
from gui.objectguid import (  # noqa: E402
    convert_objectguids,
    conversions_to_dataframe,
    detect_objectguid_column,
    objectguid_to_immutable_id,
)
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


def render_converter_tab() -> None:
    st.subheader("Convert AD ObjectGUID → Immutable ID")
    st.caption(
        "No Azure permissions required. Use a CSV export from on-premises Active Directory "
        "or any source that includes ObjectGUID."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV with ObjectGUID column",
        type=["csv"],
        key="converter_csv",
    )

    manual_guids = st.text_area(
        "Or paste ObjectGUIDs (one per line)",
        placeholder="00000000-0000-0000-0000-000000000000",
        key="converter_manual",
    )

    single_guid = st.text_input("Or convert a single ObjectGUID", key="converter_single")

    if uploaded_file is None and not manual_guids.strip() and not single_guid.strip():
        st.info("Upload a CSV, paste ObjectGUIDs, or enter one GUID above.")
        with st.expander("Example CSV"):
            st.code("samAccountName,ObjectGUID\njdoe,12345678-1234-1234-1234-123456789abc", language="csv")
        return

    object_guids: list[str] = []
    dataframe = None
    guid_column = "manual_input"

    if single_guid.strip():
        object_guids = [single_guid.strip()]
    elif uploaded_file is not None:
        dataframe = pd.read_csv(uploaded_file)
        if dataframe.empty:
            st.error("The uploaded CSV has no rows.")
            return
        st.dataframe(dataframe.head(20), use_container_width=True)
        guid_column = st.selectbox(
            "ObjectGUID column",
            options=list(dataframe.columns),
            index=list(dataframe.columns).index(detect_objectguid_column(list(dataframe.columns))),
        )
        object_guids = (
            dataframe[guid_column].dropna().astype(str).str.strip().replace("", pd.NA).dropna().tolist()
        )
    else:
        object_guids = [line.strip() for line in manual_guids.splitlines() if line.strip()]

    st.write(f"**{len(object_guids)}** ObjectGUID(s) ready to convert.")

    if st.button("Convert to immutable IDs", type="primary", key="convert_button"):
        results = convert_objectguids(object_guids)
        output = conversions_to_dataframe(results)

        st.subheader("Results")
        st.dataframe(output, use_container_width=True)

        csv_buffer = io.StringIO()
        output.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download results CSV",
            data=csv_buffer.getvalue(),
            file_name="immutable_id_conversions.csv",
            mime="text/csv",
            key="converter_download",
        )

        if dataframe is not None:
            merged = dataframe.copy()
            result_map = {r.object_guid: r.immutable_id for r in results if r.success}
            merged["Immutable ID"] = merged[guid_column].astype(str).str.strip().map(result_map)
            merged_buffer = io.StringIO()
            merged.to_csv(merged_buffer, index=False)
            st.download_button(
                "Download merged CSV",
                data=merged_buffer.getvalue(),
                file_name="users_with_immutable_ids.csv",
                mime="text/csv",
                key="converter_merged_download",
            )


def render_entra_lookup_tab() -> None:
    st.subheader("Lookup immutable ID from Entra ID")
    st.caption("Requires Graph API `User.Read.All` with admin consent.")

    with st.expander("Authentication status", expanded=not service_principal_configured()):
        if use_managed_auth_ui():
            platform = hosted_platform_name() or "Streamlit Cloud"
            if service_principal_configured():
                st.success(f"Using Azure app registration ({platform})")
                auth_mode = "service_principal"
            else:
                st.error("Azure credentials not loaded.")
                st.markdown("Streamlit Cloud → **Manage app → Settings → Secrets**:")
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
                    "service_principal": "App registration",
                }[value],
                key="entra_auth_mode",
            )
        st.caption(secrets_status_message())

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key="entra_csv")
    manual_entries = st.text_area(
        "Or paste user emails/UPNs (one per line)",
        placeholder="user@example.com",
        key="entra_manual",
    )

    if uploaded_file is None and not manual_entries.strip():
        st.info("Upload a CSV or paste user identifiers.")
        return

    if uploaded_file is not None:
        dataframe = pd.read_csv(uploaded_file)
        if dataframe.empty:
            st.error("The uploaded CSV has no rows.")
            return
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
        dataframe = None
        user_column = "manual_input"
        user_identifiers = [line.strip() for line in manual_entries.splitlines() if line.strip()]

    secrets_ready = service_principal_configured() or not use_managed_auth_ui()
    if use_managed_auth_ui() and not service_principal_configured():
        st.warning("Add Azure secrets in Streamlit Cloud, then reboot the app.")

    if st.button(
        "Fetch immutable IDs",
        type="primary",
        disabled=not user_identifiers or not secrets_ready,
        key="entra_fetch",
    ):
        with st.spinner("Querying Microsoft Graph..."):
            try:
                token = get_graph_token(resolve_auth_mode(auth_mode))
                results = fetch_immutable_ids(token, user_identifiers)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Authentication failed: {exc}")
                return

        output = results_to_dataframe(results)
        st.dataframe(output, use_container_width=True)
        csv_buffer = io.StringIO()
        output.to_csv(csv_buffer, index=False)
        st.download_button("Download results CSV", data=csv_buffer.getvalue(), key="entra_download")

        if dataframe is not None:
            merged = dataframe.copy()
            result_map = {r.user_identifier: r.on_premises_immutable_id for r in results if r.success}
            merged["Immutable ID"] = merged[user_column].map(result_map)
            merged_buffer = io.StringIO()
            merged.to_csv(merged_buffer, index=False)
            st.download_button("Download merged CSV", data=merged_buffer.getvalue(), key="entra_merged")


def main() -> None:
    apply_streamlit_secrets()

    st.set_page_config(page_title="Immutable ID Tools", page_icon="🔐", layout="wide")
    st.title("Immutable ID Tools")

    tab_convert, tab_entra = st.tabs(
        [
            "Convert ObjectGUID (no admin needed)",
            "Lookup from Entra (admin consent required)",
        ]
    )

    with tab_convert:
        render_converter_tab()

    with tab_entra:
        render_entra_lookup_tab()


if __name__ == "__main__":
    main()
