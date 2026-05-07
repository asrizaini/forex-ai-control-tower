from __future__ import annotations

import base64
import hashlib
import os
import time
from datetime import datetime
from .time_utils import utcnow
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from .credential_definitions import DEFINITION_BY_NAME, DEFINITIONS, validate_value
from .models import CredentialConfig

KEY_PATH = Path(os.getenv("CREDENTIAL_STORE_KEY_FILE", "/etc/forex-ai-control-tower/credential_store.key"))
_RUNTIME_CACHE: dict[str, tuple[float, str]] = {}


def _fallback_key_path() -> Path:
    return Path(os.getenv("CREDENTIAL_STORE_DEV_KEY_FILE", "data/runtime/credential_store.key"))


def _load_or_create_key() -> bytes:
    env_key = os.getenv("CREDENTIAL_STORE_KEY")
    if env_key:
        return env_key.encode()
    path = KEY_PATH if KEY_PATH.exists() or os.access(KEY_PATH.parent, os.W_OK) else _fallback_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_bytes().strip()
    key = Fernet.generate_key()
    path.write_bytes(key)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def _fernet() -> Fernet:
    key = _load_or_create_key()
    try:
        return Fernet(key)
    except ValueError:
        digest = hashlib.sha256(key).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str | None:
    if not encrypted_value:
        return None
    try:
        return _fernet().decrypt(encrypted_value.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def normalize_input_value(name: str, value: str | None) -> str:
    raw = (value or "").strip().replace("\r\n", "\n")
    definition = DEFINITION_BY_NAME.get(name)
    if not definition:
        return raw
    if definition.field_type in {"boolean", "select"}:
        return raw.lower()
    return raw


def value_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def mask_value(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:2]}{'*' * 8}{value[-4:]}"


def get_config_value(db: Session, name: str) -> str | None:
    record = db.scalar(select(CredentialConfig).where(CredentialConfig.name == name))
    if record and record.configured:
        decrypted = decrypt_value(record.encrypted_value)
        if decrypted is not None:
            return decrypted
    return os.getenv(name)


def runtime_value(name: str, default: str = "", *, cache_seconds: int = 5) -> str:
    env_value = os.getenv(name)
    if env_value:
        return env_value

    now = time.time()
    cached = _RUNTIME_CACHE.get(name)
    if cached and cached[0] > now:
        return cached[1]

    value = default
    try:
        from .db import SessionLocal

        db = SessionLocal()
        try:
            resolved = get_config_value(db, name)
            if resolved:
                value = resolved
        finally:
            db.close()
    except Exception:
        value = default

    _RUNTIME_CACHE[name] = (now + max(1, cache_seconds), value)
    return value


def runtime_bool(name: str, default: bool = False, *, cache_seconds: int = 5) -> bool:
    raw = runtime_value(name, "true" if default else "false", cache_seconds=cache_seconds)
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def runtime_int(name: str, default: int = 0, *, cache_seconds: int = 5) -> int:
    raw = runtime_value(name, str(default), cache_seconds=cache_seconds).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def runtime_float(name: str, default: float = 0.0, *, cache_seconds: int = 5) -> float:
    raw = runtime_value(name, str(default), cache_seconds=cache_seconds).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def clear_runtime_cache() -> None:
    _RUNTIME_CACHE.clear()


def upsert_config(db: Session, name: str, value: str, actor: str) -> CredentialConfig:
    definition = DEFINITION_BY_NAME[name]
    normalized = normalize_input_value(name, value)
    status, message = validate_value(name, normalized)
    record = db.scalar(select(CredentialConfig).where(CredentialConfig.name == name))
    if not record:
        record = CredentialConfig(name=name, category=definition.category, sensitive=definition.sensitive)
        db.add(record)
    record.category = definition.category
    record.sensitive = definition.sensitive
    record.encrypted_value = encrypt_value(normalized)
    record.value_hash = value_hash(normalized)
    record.configured = bool(normalized)
    record.validation_status = status
    record.validation_message = message
    record.updated_by = actor
    record.updated_at = utcnow()
    clear_runtime_cache()
    return record


def migrate_runtime_credentials(db: Session, actor: str = "runtime_sync") -> list[str]:
    migrated: list[str] = []
    for definition in DEFINITIONS:
        runtime_raw = os.getenv(definition.name)
        runtime_value_raw = normalize_input_value(definition.name, runtime_raw)
        if not runtime_value_raw:
            continue
        record = db.scalar(select(CredentialConfig).where(CredentialConfig.name == definition.name))
        if record and record.configured:
            decrypted = decrypt_value(record.encrypted_value)
            if decrypted == runtime_value_raw:
                continue
            if decrypted:
                continue
        upsert_config(db, definition.name, runtime_value_raw, actor)
        migrated.append(definition.name)
    return migrated


def sync_runtime_credentials(db: Session, actor: str = "runtime_sync") -> int:
    return len(migrate_runtime_credentials(db, actor))


def get_config_map(db: Session) -> dict[str, str]:
    values: dict[str, str] = {}
    for record in db.scalars(select(CredentialConfig).where(CredentialConfig.configured.is_(True))):
        value = decrypt_value(record.encrypted_value)
        if value is not None:
            values[record.name] = value
    return values


def public_status(db: Session) -> list[dict]:
    records = {record.name: record for record in db.scalars(select(CredentialConfig))}
    result = []
    for definition in DEFINITIONS:
        record = records.get(definition.name)
        decrypted = decrypt_value(record.encrypted_value) if record and record.configured else None
        runtime_env_value = os.getenv(definition.name)
        value = decrypted if decrypted is not None else runtime_env_value
        normalized = normalize_input_value(definition.name, value)
        status, message = validate_value(definition.name, normalized or "")
        source = "missing"
        if record and record.configured and decrypted is not None:
            source = "dashboard_store"
        elif runtime_env_value:
            source = "runtime_env" if not record else "runtime_env_fallback"
        result.append(
            {
                **definition.public_dict(),
                "configured": bool(normalized),
                "source": source,
                "validation_status": status,
                "validation_message": message,
                "masked_value": mask_value(normalized) if definition.sensitive else (normalized or ""),
                "updated_at": record.updated_at.isoformat() if record else None,
                "updated_by": record.updated_by if record else None,
            }
        )
    return result
