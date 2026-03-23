from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.supabase import get_supabase_client


def upload_to_storage(
    path: str,
    data: bytes,
    content_type: str,
    *,
    bucket: str | None = None,
    options: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    bucket_name = bucket or settings.supabase_assets_bucket
    storage = get_supabase_client().storage.from_(bucket_name)
    upload_options = {"content-type": content_type, "upsert": "true"}
    if options:
        upload_options.update(options)
    storage.upload(path, data, upload_options)
    return storage.get_public_url(path)


def get_public_url(path: str, *, bucket: str | None = None) -> str:
    settings = get_settings()
    bucket_name = bucket or settings.supabase_assets_bucket
    return get_supabase_client().storage.from_(bucket_name).get_public_url(path)


def upload_file_to_storage(
    local_path: str | Path,
    storage_path: str,
    *,
    bucket: str | None = None,
    content_type: str | None = None,
    options: dict[str, Any] | None = None,
) -> str:
    path = Path(local_path)
    detected_content_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return upload_to_storage(
        storage_path,
        path.read_bytes(),
        detected_content_type,
        bucket=bucket,
        options=options,
    )
