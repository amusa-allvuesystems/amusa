"""Load Azure credentials for hosted deployments."""

from __future__ import annotations

import os

import streamlit as st

from gui.config import (  # noqa: F401
    AZURE_SECRET_KEYS,
    available_auth_modes,
    default_auth_mode,
    hosted_platform_name,
    is_azure_app_service,
    is_hosted_deployment,
    is_streamlit_cloud,
    service_principal_configured,
)


def apply_streamlit_secrets() -> None:
    for key in AZURE_SECRET_KEYS:
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = str(st.secrets[key])
