from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import os
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from localization.locale_manager import normalize_language


LABELS = {
    "en": {
        "summary": "Summary",
        "next_action": "Next action",
        "risk_status": "Risk status",
        "result": "Result",
        "safe_note": "Safe visible summary only. Hidden reasoning and secrets are not displayed.",
    },
    "ms-MY": {
        "summary": "Ringkasan",
        "next_action": "Tindakan seterusnya",
        "risk_status": "Status risiko",
        "result": "Keputusan",
        "safe_note": "Ringkasan selamat sahaja. Penaakulan tersembunyi dan rahsia tidak dipaparkan.",
    },
}

PHRASE_MAP_MS_MY = {
    "System status: control API, dashboard, monitoring, worker heartbeats, and Agent Theater are online. The tower remains in monitor-only safety mode while real market/news/strategy adapters are being wired.": (
        "Status sistem: Control API, dashboard, pemantauan, heartbeat worker, dan Agent Theater sedang online. "
        "Menara kawalan kekal dalam mod keselamatan monitor-only sementara adapter pasaran, berita, dan strategi sebenar disambungkan."
    ),
    "I received your message. I can handle general questions, planning, explanations, operator requests, and safe task routing. For trading or infrastructure actions, I will coordinate the relevant agent and keep governance, audit, and approval gates in place.": (
        "Saya terima mesej anda. Saya boleh bantu soalan umum, perancangan, penerangan, permintaan operator, dan penghalaan tugas yang selamat. "
        "Untuk tindakan dagangan atau infrastruktur, saya akan selaraskan agen berkaitan dan kekalkan tadbir urus, audit, serta pintu kelulusan."
    ),
    "News adapter is not connected yet. Until ForexFactory/economic-calendar integration is live, high-impact news status stays conservative.": (
        "Adapter berita belum disambungkan. Selagi integrasi kalendar ekonomi belum aktif, status berita berimpak tinggi kekal konservatif."
    ),
    "No live setup is under review. When Strategy Agent proposes a demo signal, I will check score, rationale, duplicate risk, and approval requirements.": (
        "Tiada setup live sedang disemak. Apabila Strategy Agent mencadangkan signal demo, saya akan semak skor, rasional, risiko pendua, dan keperluan kelulusan."
    ),
    "Notification channels are not connected yet. I will not claim Telegram or mobile push delivery until credentials and channel tests pass.": (
        "Saluran notifikasi belum disambungkan. Saya tidak akan menganggap Telegram atau mobile push berjaya sehingga kredensial dan ujian saluran lulus."
    ),
}

STATUS_MAP_MS_MY = {
    "read_only_no_trade_execution": "baca_sahaja_tiada_pelaksanaan_dagangan",
    "read_only_chat_no_execution": "chat_baca_sahaja_tiada_pelaksanaan",
    "execution_guarded_monitor_only": "execution_guard_dalam_mod_monitor_only",
    "no_execution_requested": "tiada_pelaksanaan_diminta",
    "news_safe_mode": "mod_selamat_berita",
    "manual_review_required": "semakan_manual_diperlukan",
    "auto_execution_disabled": "pelaksanaan_auto_dinyahaktifkan",
    "order_send_blocked_without_guard_token": "order_send_disekat_tanpa_guard_token",
}


def _app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(os.getenv("APP_TIMEZONE") or os.getenv("TZ") or "Asia/Kuala_Lumpur")
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Kuala_Lumpur")


def _display_timestamp(value: Any) -> str:
    text = str(value or "")
    if not text:
        return text
    if text.endswith("Z"):
        try:
            parsed = datetime.fromisoformat(text[:-1] + "+00:00")
        except ValueError:
            return text
        return parsed.astimezone(_app_timezone()).strftime("%Y-%m-%d %I:%M:%S %p GMT+8")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(_app_timezone()).strftime("%Y-%m-%d %I:%M:%S %p GMT+8")


def render_event(event: dict[str, Any], language: str = "en") -> dict[str, Any]:
    normalized = normalize_language(language)
    if normalized == "auto":
        normalized = "en"
    labels = LABELS.get(normalized, LABELS["en"])
    rendered = deepcopy(event)
    if "timestamp" in rendered:
        rendered["timestamp"] = _display_timestamp(rendered["timestamp"])
    summary = str(event.get("summary", ""))
    next_action = str(event.get("next_action", ""))
    risk_status = str(event.get("risk_status", ""))
    if normalized == "ms-MY":
        summary = PHRASE_MAP_MS_MY.get(summary, summary)
        risk_status = STATUS_MAP_MS_MY.get(risk_status, risk_status)
        if next_action == "Continue monitoring.":
            next_action = "Teruskan pemantauan."
    rendered["display"] = {
        "language": normalized,
        "labels": labels,
        "summary": summary,
        "next_action": next_action,
        "risk_status": risk_status,
        "safe_note": labels["safe_note"],
    }
    return rendered


def render_events(events: list[dict[str, Any]], language: str = "en") -> list[dict[str, Any]]:
    return [render_event(event, language) for event in events]
