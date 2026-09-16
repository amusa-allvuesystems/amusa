"""FastAPI server for Entra ID immutable ID lookups."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.azure_graph import UserImmutableIdResult, fetch_immutable_ids, get_graph_token  # noqa: E402
from gui.config import (  # noqa: E402
    available_auth_modes,
    default_auth_mode,
    hosted_platform_name,
    is_hosted_deployment,
    service_principal_configured,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

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

app = FastAPI(
    title="Entra Immutable ID Lookup",
    description="Fetch onPremisesImmutableId values from Microsoft Entra ID.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LookupRequest(BaseModel):
    users: list[str] = Field(..., min_length=1, max_length=500)
    auth_mode: str | None = None


class UserResult(BaseModel):
    input: str
    display_name: str | None = None
    user_principal_name: str | None = None
    immutable_id: str | None = None
    success: bool
    error: str | None = None


class LookupResponse(BaseModel):
    results: list[UserResult]
    processed: int
    succeeded: int
    errors: int


class AuthStatusResponse(BaseModel):
    hosted: bool
    platform: str | None
    service_principal_configured: bool
    available_auth_modes: list[str]
    default_auth_mode: str
    ready: bool


def detect_user_column(columns: list[str]) -> str | None:
    normalized = {column: column.strip().lower() for column in columns}
    for candidate in USER_COLUMN_CANDIDATES:
        for column, column_name in normalized.items():
            if column_name == candidate:
                return column
    return columns[0] if columns else None


def result_to_model(result: UserImmutableIdResult) -> UserResult:
    return UserResult(
        input=result.user_identifier,
        display_name=result.display_name,
        user_principal_name=result.user_principal_name,
        immutable_id=result.on_premises_immutable_id,
        success=result.success,
        error=result.error,
    )


def resolve_auth_mode(requested: str | None) -> str:
    mode = requested or default_auth_mode()
    allowed = available_auth_modes()
    if mode not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid auth mode '{mode}'. Allowed: {', '.join(allowed)}",
        )
    if is_hosted_deployment() and not service_principal_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Azure credentials missing. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, "
                "and AZURE_CLIENT_SECRET in app settings."
            ),
        )
    return mode


def run_lookup(user_identifiers: list[str], auth_mode: str) -> LookupResponse:
    cleaned = [value.strip() for value in user_identifiers if value and value.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail="No valid user identifiers provided.")

    if len(cleaned) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 users per request.")

    try:
        token = get_graph_token(auth_mode)
        results = fetch_immutable_ids(token, cleaned)
    except Exception as exc:  # noqa: BLE001 - surface auth errors to client
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}") from exc

    models = [result_to_model(result) for result in results]
    succeeded = sum(1 for result in models if result.success)
    return LookupResponse(
        results=models,
        processed=len(models),
        succeeded=succeeded,
        errors=len(models) - succeeded,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    configured = service_principal_configured()
    return AuthStatusResponse(
        hosted=is_hosted_deployment(),
        platform=hosted_platform_name(),
        service_principal_configured=configured,
        available_auth_modes=available_auth_modes(),
        default_auth_mode=default_auth_mode(),
        ready=configured or not is_hosted_deployment(),
    )


@app.post("/api/lookup", response_model=LookupResponse)
def lookup_users(request: LookupRequest) -> LookupResponse:
    auth_mode = resolve_auth_mode(request.auth_mode)
    return run_lookup(request.users, auth_mode)


@app.post("/api/lookup/csv", response_model=LookupResponse)
async def lookup_csv(
    file: UploadFile = File(...),
    column: str | None = None,
    auth_mode: str | None = None,
) -> LookupResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row.")

    selected_column = column or detect_user_column(list(reader.fieldnames))
    if not selected_column or selected_column not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{selected_column}' not found. Available: {', '.join(reader.fieldnames)}",
        )

    user_identifiers = [
        (row.get(selected_column) or "").strip()
        for row in reader
        if (row.get(selected_column) or "").strip()
    ]

    resolved_auth = resolve_auth_mode(auth_mode)
    return run_lookup(user_identifiers, resolved_auth)


@app.get("/api/csv/columns")
async def csv_columns(file: UploadFile = File(...)) -> dict[str, list[str] | str | None]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row.")

    columns = list(reader.fieldnames)
    return {
        "columns": columns,
        "suggested_column": detect_user_column(columns),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
