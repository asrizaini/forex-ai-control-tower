from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from .credential_definitions import DEFINITION_BY_NAME, DEFINITIONS, validate_value
from .models import CredentialConfig

KEY_PATH = Path(os.getenv("CREDENTIAL_STORE_KEY_FILE", "/etc/forex-ai-control-tower/credential_store.key"))


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
        return decrypt_value(record.encrypted_value)
    return os.getenv(name)


def get_config_map(db: Session) -> dict[str, str]:
    values: dict[str, str] = {}
    for record in db.scalars(select(CredentialConfig).where(CredentialConfig.configured.is_(True))):
        value = decrypt_value(record.encrypted_value)
        if value is not None:
            values[record.name] = value
    return values


def upsert_config(db: Session, name: str, value: str, actor: str) -> CredentialConfig:
    definition = DEFINITION_BY_NAME[name]
    status, message = validate_value(name, value)
    record = db.scalar(select(CredentialConfig).where(CredentialConfig.name == name))
    if not record:
        record = CredentialConfig(name=name, category=definition.category, sensitive=definition.sensitive)
        db.add(record)
    record.category = definition.category
    record.sensitive = definition.sensitive
    record.encrypted_value = encrypt_value(value)
    record.value_hash = value_hash(value)
    record.configured = bool(value)
    record.validation_status = status
    record.validation_message = message
    record.updated_by = actor
    record.updated_at = datetime.utcnow()
    return record


def public_status(db: Session) -> list[dict]:
    records = {record.name: record for record in db.scalars(select(CredentialConfig))}
    result = []
    for definition in DEFINITIONS:
        record = records.get(definition.name)
        value = decrypt_value(record.encrypted_value) if record and record.configured else os.getenv(definition.name)
        status, message = validate_value(definition.name, value or "")
        result.append(
            {
                **definition.public_dict(),
                "configured": bool(value),
                "source": "dashboard_store" if record and record.configured else ("runtime_env" if os.getenv(definition.name) else "missing"),
                "validation_status": status,
                "validation_message": message,
                "masked_value": mask_value(value) if definition.sensitive else (value or ""),
                "updated_at": record.updated_at.isoformat() if record else None,
                "updated_by": record.updated_by if record else None,
            }
        )
    return result
