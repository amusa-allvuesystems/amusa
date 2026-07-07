"""Load Azure credentials for hosted deployments."""

from __future__ import annotations

import os

import streamlit as st

AZURE_SECRET_KEYS = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")


def is_streamlit_cloud() -> bool:
    return os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud"


def is_azure_app_service() -> bool:
    return bool(os.getenv("WEBSITE_SITE_NAME"))


def is_hosted_deployment() -> bool:
    return is_streamlit_cloud() or is_azure_app_service()


def apply_streamlit_secrets() -> None:
    for key in AZURE_SECRET_KEYS:
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = str(st.secrets[key])


def service_principal_configured() -> bool:
    return all(os.environ.get(name) for name in AZURE_SECRET_KEYS)


def default_auth_mode() -> str:
    if is_hosted_deployment() or service_principal_configured():
        return "service_principal"
    return "default"


def hosted_platform_name() -> str | None:
    if is_azure_app_service():
        return "Azure App Service"
    if is_streamlit_cloud():
        return "Streamlit Cloud"
    return None
