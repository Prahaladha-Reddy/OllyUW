from __future__ import annotations


WORKER_READY     = "worker_ready"
STATUS           = "status"
MODEL_START      = "model_start"
MODEL_END        = "model_end"
TEXT_DELTA       = "text_delta"
TOOL_CALL        = "tool_call"
TOOL_RESULT      = "tool_result"
FINAL            = "final"
MESSAGE_RECEIVED = "message_received"
MESSAGE_ACKED    = "message_acked"
ERROR            = "error"

# Subagent lifecycle events — published from runner.py so the frontend
# can show real-time progress for each parallel subagent.
SUBAGENT_START   = "subagent_start"   # subagent spawned
SUBAGENT_DONE    = "subagent_done"    # subagent finished (success or error)
