from __future__ import annotations

import json
import time

from agent import tools as _tools
from agent.agent_loop import process_message
from agent.config import (
    CONSUMER_GROUP,
    CONSUMER_NAME,
    DEFAULT_MODEL,
    HEARTBEAT_INTERVAL,
    INPUT_STREAM,
    OUTPUT_CHANNEL,
    SESSION_ID,
    WORKSPACE,
)
from agent.events import ERROR, MESSAGE_ACKED, MESSAGE_RECEIVED, WORKER_READY
from agent.log import log
from agent.redis_io import client as redis_client
from agent.redis_io import ensure_consumer_group, heartbeat, publish


_tools.WORKSPACE = WORKSPACE


def main() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    ensure_consumer_group()
    log.info(
        "worker_ready session=%s workspace=%s stream=%s channel=%s",
        SESSION_ID, WORKSPACE, INPUT_STREAM, OUTPUT_CHANNEL,
    )
    publish({"type": WORKER_READY, "text": "Agent worker is running"})

    r = redis_client()
    last_heartbeat = 0.0

    while True:
        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            heartbeat()
            last_heartbeat = now

        response = r.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {INPUT_STREAM: ">"},
            count=1,
            block=5000,
        )
        if not response:
            continue

        for _stream, entries in response:
            for message_id, fields in entries:
                _handle_entry(r, message_id, fields)

        time.sleep(0.05)


def _handle_entry(r, message_id: str, fields: dict) -> None:
    try:
        raw = fields.get("data", "{}")
        payload = json.loads(raw)
        user_text = str(payload.get("message", ""))
        model = str(payload.get("model") or DEFAULT_MODEL)
        log.info("message_received id=%s model=%s len=%d",
                 message_id, model, len(user_text))
        publish({"type": MESSAGE_RECEIVED, "message_id": message_id, "model": model})
        process_message(user_text, model)
        r.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)
        publish({"type": MESSAGE_ACKED, "message_id": message_id})
    except Exception as exc:
        log.exception("failed to process message id=%s", message_id)
        publish({
            "type": ERROR,
            "text": f"{type(exc).__name__}: {exc}",
            "message_id": message_id,
        })
        r.xack(INPUT_STREAM, CONSUMER_GROUP, message_id)


if __name__ == "__main__":
    main()
