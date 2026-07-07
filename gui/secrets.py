"""Load Azure credentials for hosted deployments."""

from __future__ import annotations

import os

import streamlit as st

AZURE_SECRET_KEYS = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")

# Flat keys and nested [azure] section aliases
SECRET_ALIASES: dict[str, tuple[str, ...]] = {
    "AZURE_TENANT_ID": ("AZURE_TENANT_ID", "tenant_id", "TENANT_ID"),
    "AZURE_CLIENT_ID": ("AZURE_CLIENT_ID", "client_id", "CLIENT_ID"),
    "AZURE_CLIENT_SECRET": ("AZURE_CLIENT_SECRET", "client_secret", "CLIENT_SECRET"),
}


def is_streamlit_cloud() -> bool:
    if os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud":
        return True
    if os.getenv("STREAMLIT_SHARING"):
        return True
    hostname = os.getenv("HOSTNAME", "").lower()
    return "streamlit" in hostname


def is_azure_app_service() -> bool:
    return bool(os.getenv("WEBSITE_SITE_NAME"))


def is_hosted_deployment() -> bool:
    return is_streamlit_cloud() or is_azure_app_service()


def _read_secret_value(*keys: str) -> str | None:
    for key in keys:
        if key in st.secrets:
            value = st.secrets[key]
            if value:
                return str(value).strip()
        if "azure" in st.secrets and key in st.secrets["azure"]:
            value = st.secrets["azure"][key]
            if value:
                return str(value).strip()
    return None


def apply_streamlit_secrets() -> None:
    for env_key, aliases in SECRET_ALIASES.items():
        if os.environ.get(env_key):
            continue
        value = _read_secret_value(*aliases)
        if value:
            os.environ[env_key] = value


def service_principal_configured() -> bool:
    return all(os.environ.get(name) for name in AZURE_SECRET_KEYS)


def missing_secret_keys() -> list[str]:
    return [name for name in AZURE_SECRET_KEYS if not os.environ.get(name)]


def resolve_auth_mode(requested_mode: str) -> str:
    apply_streamlit_secrets()
    if service_principal_configured():
        return "service_principal"
    if is_hosted_deployment() or requested_mode == "service_principal":
        missing = ", ".join(missing_secret_keys())
        raise ValueError(
            "Azure app registration credentials are not configured. "
            f"Missing: {missing}. "
            "In Streamlit Cloud go to Manage app → Settings → Secrets and add:\n\n"
            "AZURE_TENANT_ID = \"your-tenant-id\"\n"
            "AZURE_CLIENT_ID = \"your-client-id\"\n"
            "AZURE_CLIENT_SECRET = \"your-client-secret\""
        )
    return requested_mode


def default_auth_mode() -> str:
    apply_streamlit_secrets()
    if is_hosted_deployment() or service_principal_configured():
        return "service_principal"
    return "default"


def hosted_platform_name() -> str | None:
    if is_azure_app_service():
        return "Azure App Service"
    if is_streamlit_cloud():
        return "Streamlit Cloud"
    return None


def secrets_status_message() -> str:
    apply_streamlit_secrets()
    if service_principal_configured():
        return "Azure credentials loaded"
    missing = missing_secret_keys()
    if missing:
        return f"Missing: {', '.join(missing)}"
    return "Azure credentials not configured"
