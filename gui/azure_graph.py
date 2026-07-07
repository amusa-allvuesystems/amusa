"""Microsoft Graph helpers for Entra ID immutable ID lookups."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote

import requests
from azure.identity import (
    ClientSecretCredential,
    DefaultAzureCredential,
    InteractiveBrowserCredential,
)


GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@dataclass
class UserImmutableIdResult:
    user_identifier: str
    display_name: str | None = None
    user_principal_name: str | None = None
    on_premises_immutable_id: str | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def build_credential(auth_mode: str):
    if auth_mode == "service_principal":
        tenant_id = os.environ["AZURE_TENANT_ID"]
        client_id = os.environ["AZURE_CLIENT_ID"]
        client_secret = os.environ["AZURE_CLIENT_SECRET"]
        return ClientSecretCredential(tenant_id, client_id, client_secret)

    if auth_mode == "browser":
        tenant_id = os.environ.get("AZURE_TENANT_ID")
        return InteractiveBrowserCredential(tenant_id=tenant_id)

    return DefaultAzureCredential()


def get_graph_token(auth_mode: str) -> str:
    if auth_mode == "service_principal":
        missing = [
            key for key in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")
            if not os.environ.get(key)
        ]
        if missing:
            raise ValueError(
                f"Service principal credentials missing: {', '.join(missing)}"
            )

    credential = build_credential(auth_mode)
    return credential.get_token(GRAPH_SCOPE).token


def _graph_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fetch_user_immutable_id(token: str, user_identifier: str) -> UserImmutableIdResult:
    encoded_id = quote(user_identifier, safe="")
    url = (
        f"{GRAPH_BASE}/users/{encoded_id}"
        "?$select=displayName,userPrincipalName,onPremisesImmutableId"
    )

    try:
        response = requests.get(url, headers=_graph_headers(token), timeout=30)
    except requests.RequestException as exc:
        return UserImmutableIdResult(user_identifier=user_identifier, error=str(exc))

    if response.status_code == 404:
        return UserImmutableIdResult(
            user_identifier=user_identifier,
            error="User not found in Entra ID",
        )

    if not response.ok:
        detail = response.text.strip() or response.reason
        return UserImmutableIdResult(
            user_identifier=user_identifier,
            error=f"Graph API error {response.status_code}: {detail}",
        )

    payload = response.json()
    return UserImmutableIdResult(
        user_identifier=user_identifier,
        display_name=payload.get("displayName"),
        user_principal_name=payload.get("userPrincipalName"),
        on_premises_immutable_id=payload.get("onPremisesImmutableId"),
    )


def fetch_immutable_ids(
    token: str,
    user_identifiers: Iterable[str],
) -> list[UserImmutableIdResult]:
    results: list[UserImmutableIdResult] = []
    for user_identifier in user_identifiers:
        identifier = str(user_identifier).strip()
        if not identifier:
            continue
        results.append(fetch_user_immutable_id(token, identifier))
    return results
