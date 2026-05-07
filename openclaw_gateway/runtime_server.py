from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

from control.api.credential_store import runtime_value


LOCAL_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def _now_iso_local() -> str:
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).isoformat()


class OpenClawRuntimeHandler(BaseHTTPRequestHandler):
    server_version = "OpenClawRuntime/1.0"

    def _token_ok(self) -> bool:
        required = runtime_value("OPENCLAW_API_TOKEN", "").strip()
        if not required:
            return True
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        provided = auth.split(" ", 1)[1].strip()
        return bool(provided) and provided == required

    def _json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            return self._json(
                200,
                {
                    "status": "ok",
                    "service": "openclaw-runtime",
                    "timezone": "Asia/Kuala_Lumpur",
                    "now": _now_iso_local(),
                },
            )
        self._json(404, {"ok": False, "reason": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._token_ok():
            return self._json(401, {"ok": False, "reason": "unauthorized"})

        payload = self._read_json()
        message = str(payload.get("message", "")).strip()
        language = str(payload.get("language", "en")).strip()
        if language not in {"en", "ms-MY", "auto"}:
            language = "en"

        now = _now_iso_local()

        if self.path == "/chat":
            if language == "ms-MY":
                reply = (
                    "OpenClaw runtime aktif. Saya hanya menyokong ringkasan selamat, status sistem, "
                    "dan tindakan API yang diluluskan. Tiada pelaksanaan dagangan terus."
                )
            else:
                reply = (
                    "OpenClaw runtime is active. I support safe summaries, system status, "
                    "and approved API actions only. No direct trade execution."
                )
            if message:
                reply = f"{reply} | Message received at {now}."
            return self._json(
                200,
                {"ok": True, "reply": reply, "received_at": now, "safe_mode": True, "trade_execution_allowed": False},
            )

        if self.path == "/status/query":
            target = str(payload.get("target", "system")).strip().lower() or "system"
            if language == "ms-MY":
                summary = f"Ringkasan '{target}' pada {now}: runtime OpenClaw stabil dalam mod selamat."
            else:
                summary = f"'{target}' summary at {now}: OpenClaw runtime is healthy in safe mode."
            return self._json(200, {"ok": True, "target": target, "summary": summary, "trade_execution_allowed": False})

        if self.path == "/summary/daily":
            if language == "ms-MY":
                summary = (
                    f"Ringkasan harian ({now}): runtime OpenClaw aktif dan semua tindakan kekal berpagar keselamatan."
                )
            else:
                summary = f"Daily summary ({now}): OpenClaw runtime is active and all actions remain policy-gated."
            return self._json(200, {"ok": True, "summary": summary, "trade_execution_allowed": False})

        self._json(404, {"ok": False, "reason": "unsupported_path"})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        # Keep default console logs minimal and never include request bodies/tokens.
        return


def main() -> None:
    host = os.getenv("OPENCLAW_RUNTIME_HOST", "0.0.0.0")
    try:
        port = int(os.getenv("OPENCLAW_RUNTIME_PORT", "8600"))
    except ValueError:
        port = 8600
    server = ThreadingHTTPServer((host, port), OpenClawRuntimeHandler)
    print(f"openclaw-runtime listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
