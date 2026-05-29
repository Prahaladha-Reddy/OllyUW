from __future__ import annotations

import json
import socket
from typing import Any

import redis

from agent.config import (
    ACTIVITY_KEY,
    ACTIVITY_TTL,
    CONSUMER_GROUP,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_KEY,
    INPUT_STREAM,
    OUTPUT_CHANNEL,
    REDIS_URL,
    SESSION_ID,
)

# TCP keepalive intervals. Without these, socket_keepalive=True alone uses the
# OS default idle time (~2 hours on Linux) before probing a silent peer. When
# the sandbox idle-pauses and later resumes, the socket to Upstash is silently
# dead; with these intervals the kernel detects it in ~1 minute (30s idle, then
# 3 probes 10s apart) and the next blocking read fails fast so we reconnect,
# instead of the worker hanging forever in xreadgroup. Linux-only constants, so
# probe for them defensively.
_KEEPALIVE_INTERVALS = {"TCP_KEEPIDLE": 30, "TCP_KEEPINTVL": 10, "TCP_KEEPCNT": 3}
_KEEPALIVE_OPTS: dict[int, int] = {}
for _name, _secs in _KEEPALIVE_INTERVALS.items():
    _const = getattr(socket, _name, None)
    if _const is not None:
        _KEEPALIVE_OPTS[_const] = _secs

# Long-lived consumer against a managed Redis (Upstash over TLS).
# socket_timeout MUST stay larger than the worker's XREADGROUP BLOCK window
# (5s, set in worker.py): a healthy blocking read returns well within 10s, but
# a half-open socket (post-resume) trips the timeout and our retry loop
# reconnects instead of hanging on a dead connection.
_client: redis.Redis = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_keepalive=True,
    socket_keepalive_options=_KEEPALIVE_OPTS or None,
    socket_timeout=10,
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


def touch_activity() -> None:
    """Mark the sandbox as recently active.

    Called when the worker begins processing a message. The backend watcher
    extends the E2B sandbox timeout only while this key exists. TTL = 20 min,
    so after the last message finishes and no new ones arrive, the key expires
    and the watcher stops extending, letting E2B idle-pause the sandbox.
    """
    _client.set(ACTIVITY_KEY, "1", ex=ACTIVITY_TTL)


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


def reconnect() -> None:
    """Drop all pooled connections so the next command dials a fresh socket.

    Called by the worker after a read error (e.g. the post-resume dead socket)
    so recovery does not depend on redis-py's internal retry heuristics.
    """
    try:
        _client.connection_pool.disconnect()
    except Exception:
        pass
