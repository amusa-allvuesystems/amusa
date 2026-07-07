"""Load Azure credentials for hosted deployments."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import streamlit as st

AZURE_SECRET_KEYS = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")

SECRET_ALIASES: dict[str, tuple[str, ...]] = {
    "AZURE_TENANT_ID": ("AZURE_TENANT_ID", "tenant_id", "TENANT_ID"),
    "AZURE_CLIENT_ID": ("AZURE_CLIENT_ID", "client_id", "CLIENT_ID"),
    "AZURE_CLIENT_SECRET": ("AZURE_CLIENT_SECRET", "client_secret", "CLIENT_SECRET"),
}

SECRETS_TEMPLATE = """AZURE_TENANT_ID = "your-tenant-id"
AZURE_CLIENT_ID = "your-client-id"
AZURE_CLIENT_SECRET = "your-client-secret"
"""


def _local_secrets_file_exists() -> bool:
    return Path(".streamlit/secrets.toml").exists()


def is_streamlit_cloud() -> bool:
    if os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud":
        return True
    if os.getenv("STREAMLIT_SHARING"):
        return True

    hostname = os.getenv("HOSTNAME", "").lower()
    if "streamlit" in hostname:
        return True

    # Streamlit Cloud: headless server, no local secrets file, no Azure CLI
    if (
        os.getenv("STREAMLIT_SERVER_HEADLESS") == "true"
        and not is_azure_app_service()
        and not _local_secrets_file_exists()
        and shutil.which("az") is None
    ):
        return True

    return False


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


def has_streamlit_secrets_configured() -> bool:
    try:
        for aliases in SECRET_ALIASES.values():
            if _read_secret_value(*aliases):
                return True
    except Exception:  # noqa: BLE001 - secrets may be unavailable locally
        return False
    return False


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


def use_managed_auth_ui() -> bool:
    """True when the app should not show local-only auth options (az login)."""
    apply_streamlit_secrets()
    return (
        is_hosted_deployment()
        or service_principal_configured()
        or has_streamlit_secrets_configured()
    )


def resolve_auth_mode(requested_mode: str) -> str:
    apply_streamlit_secrets()
    if service_principal_configured():
        return "service_principal"
    if use_managed_auth_ui() or requested_mode == "service_principal":
        missing = ", ".join(missing_secret_keys())
        raise ValueError(
            "Azure app registration credentials are not configured. "
            f"Missing: {missing}. "
            "In Streamlit Cloud: Manage app → Settings → Secrets, paste the template, "
            "save, then Reboot app."
        )
    return requested_mode


def default_auth_mode() -> str:
    apply_streamlit_secrets()
    if use_managed_auth_ui():
        return "service_principal"
    return "service_principal" if service_principal_configured() else "default"


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
