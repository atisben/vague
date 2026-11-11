"""vague log-event command: record a Claude Code hook event."""

from __future__ import annotations

import json
import sys

from vague.sdk.core.logging import get_logger


def cmd_log_event() -> None:
    """Read hook JSON on stdin and append a skill_start event.

    Runs on every Skill tool call and prompt, so it never prints, never raises, and always
    exits 0: a broken log must not slow or break the user's session.
    """
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            get_logger().warning("log-event: payload is not a JSON object")
            return

        from vague.sdk.core.config import get_config
        if get_config().telemetry == "off":
            return

        from vague.sdk.core.events import append_event, parse_hook_payload
        event = parse_hook_payload(payload=payload)
        if event is not None:
            append_event(event=event)
    except Exception as e:
        get_logger().warning("log-event failed: %s", e)
