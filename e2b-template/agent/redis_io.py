from __future__ import annotations

import json
from typing import Any

import redis

from agent.config import (
    CONSUMER_GROUP,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_KEY,
    INPUT_STREAM,
    OUTPUT_CHANNEL,
    REDIS_URL,
    SESSION_ID,
)

# Long-lived consumer against a managed Redis (Upstash over TLS): keep the
# connection warm and let redis-py reconnect transparently after an idle drop.
# socket_timeout stays unset (None) so blocking XREADGROUP reads wait for the
# server-side BLOCK window instead of tripping a client-side socket timeout.
_client: redis.Redis = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_keepalive=True,
    health_check_interval=30,
    retry_on_timeout=True,
)
_seq: int = 0


def publish(event: dict[str, Any]) -> None:
    """
    Send a single event on OUTPUT_CHANNEL. We stamp every event with the
    session_id (so a subscriber listening to many sessions can demux) and
    a monotonic `seq` (so the frontend can detect dropped or reordered
    deliveries).
    """
    global _seq
    _seq += 1
    event.setdefault("session_id", SESSION_ID)
    event["seq"] = _seq
    _client.publish(OUTPUT_CHANNEL, json.dumps(event, ensure_ascii=False))


def heartbeat() -> None:
    """Refresh the sandbox liveness key. Read by backend `worker_alive`."""
    _client.set(HEARTBEAT_KEY, "1", ex=HEARTBEAT_INTERVAL * 3)


def ensure_consumer_group() -> None:
    """Create the agent consumer group on the input stream if it doesn't exist."""
    try:
        _client.xgroup_create(INPUT_STREAM, CONSUMER_GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def client() -> redis.Redis:
    """Hand the raw client out to the main loop's xreadgroup."""
    return _client
