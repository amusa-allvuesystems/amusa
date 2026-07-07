"""Convert on-premises AD ObjectGUID values to Entra immutable ID format."""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass


OBJECTGUID_COLUMN_CANDIDATES = (
    "objectguid",
    "object_guid",
    "guid",
    "adobjectguid",
    "ad_object_guid",
)


@dataclass
class ObjectGuidConversionResult:
    object_guid: str
    immutable_id: str | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def objectguid_to_immutable_id(object_guid: str) -> str:
    """Match PowerShell: [Convert]::ToBase64String([guid]::Parse($id).ToByteArray())."""
    guid = uuid.UUID(str(object_guid).strip())
    return base64.b64encode(guid.bytes_le).decode("ascii")


def convert_objectguid(object_guid: str) -> ObjectGuidConversionResult:
    value = str(object_guid).strip()
    if not value:
        return ObjectGuidConversionResult(object_guid=object_guid, error="Empty ObjectGUID")

    try:
        immutable_id = objectguid_to_immutable_id(value)
    except (ValueError, AttributeError) as exc:
        return ObjectGuidConversionResult(object_guid=value, error=f"Invalid ObjectGUID: {exc}")

    return ObjectGuidConversionResult(object_guid=value, immutable_id=immutable_id)


def convert_objectguids(object_guids: list[str]) -> list[ObjectGuidConversionResult]:
    return [convert_objectguid(value) for value in object_guids]


def detect_objectguid_column(columns: list[str]) -> str | None:
    normalized = {column: column.strip().lower() for column in columns}
    for candidate in OBJECTGUID_COLUMN_CANDIDATES:
        for column, column_name in normalized.items():
            if column_name == candidate:
                return column
    return columns[0] if columns else None


def conversions_to_dataframe(results: list[ObjectGuidConversionResult]):
    import pandas as pd

    return pd.DataFrame(
        [
            {
                "ObjectGUID": result.object_guid,
                "Immutable ID": result.immutable_id,
                "Status": "OK" if result.success else "Error",
                "Error": result.error or "",
            }
            for result in results
        ]
    )
