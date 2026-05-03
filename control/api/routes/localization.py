from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from localization.language_detector import detect_language
from localization.locale_manager import DO_NOT_TRANSLATE, SUPPORTED_LANGUAGES, load_locale, normalize_language, translate_key

router = APIRouter(prefix="/localization", tags=["localization"])


class DetectRequest(BaseModel):
    text: str = Field(max_length=1000)


@router.get("")
def list_resource() -> dict:
    return {"module": "localization", "description": "Language and locale support", "mode": "production-required"}


@router.get("/languages")
def languages() -> dict:
    return {"supported": SUPPORTED_LANGUAGES, "default": "en", "internal": "en", "do_not_translate": sorted(DO_NOT_TRANSLATE)}


@router.get("/locales/{language}/{namespace}")
def locale(language: str, namespace: str) -> dict:
    normalized = normalize_language(language)
    return {"language": normalized, "namespace": namespace, "messages": load_locale(normalized, namespace)}


@router.get("/translate/{language}/{namespace}/{key}")
def translate(language: str, namespace: str, key: str) -> dict:
    normalized = normalize_language(language)
    return {"language": normalized, "namespace": namespace, "key": key, "text": translate_key(namespace, key, normalized)}


@router.post("/detect")
def detect(payload: DetectRequest) -> dict:
    return {"language": detect_language(payload.text)}

