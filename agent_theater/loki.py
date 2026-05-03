from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


def push_event(event: dict[str, Any]) -> bool:
    url = os.getenv("LOKI_PUSH_URL", "http://10.10.1.81:3100/loki/api/v1/push")
    labels = {
        "app": "forex-ai-control-tower",
        "stream": "agent-theater",
        "agent": str(event.get("agent", "unknown")).replace(" ", "_"),
        "room": str(event.get("stream", "Live Chat View")).replace(" ", "_"),
    }
    payload = {
        "streams": [
            {
                "stream": labels,
                "values": [[str(time.time_ns()), json.dumps(event, separators=(",", ":"))]],
            }
        ]
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False
