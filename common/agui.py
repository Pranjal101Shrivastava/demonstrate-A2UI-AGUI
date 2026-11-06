"""AG-UI event constructors (Agent-User Interaction Protocol).

AG-UI is a TRANSPORT: a run is a stream of typed JSON events from agent to
frontend (here over SSE). Names and fields follow the AG-UI spec
(https://docs.ag-ui.com/concepts/events). The frontend sends a RunAgentInput
{threadId, runId, messages, tools, state, forwardedProps} to start a run.
"""
import itertools
import json

_ids = itertools.count(1)


def new_id(prefix):
    return f"{prefix}_{next(_ids)}"


def run_started(thread_id, run_id):
    return {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}


def run_finished(thread_id, run_id, result=None):
    e = {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}
    if result is not None:
        e["result"] = result
    return e


def run_error(message):
    return {"type": "RUN_ERROR", "message": message}


def text_message(text, chunks):
    """Yield TEXT_MESSAGE_START / CONTENT* / END for one assistant message."""
    mid = new_id("msg")
    yield {"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"}
    for c in chunks(text):
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": c}
    yield {"type": "TEXT_MESSAGE_END", "messageId": mid}


def tool_call(name, args, chunks, result=None):
    """Yield TOOL_CALL_START / ARGS* / END (+ RESULT). Arguments stream as JSON text."""
    tid = new_id("call")
    yield {"type": "TOOL_CALL_START", "toolCallId": tid, "toolCallName": name}
    for c in chunks(json.dumps(args)):
        yield {"type": "TOOL_CALL_ARGS", "toolCallId": tid, "delta": c}
    yield {"type": "TOOL_CALL_END", "toolCallId": tid}
    if result is not None:
        yield {"type": "TOOL_CALL_RESULT", "messageId": new_id("msg"), "toolCallId": tid, "role": "tool", "content": json.dumps(result)}


def state_snapshot(snapshot):
    return {"type": "STATE_SNAPSHOT", "snapshot": snapshot}


def state_delta(ops):
    return {"type": "STATE_DELTA", "delta": ops}


def custom(name, value):
    return {"type": "CUSTOM", "name": name, "value": value}


def last_user_text(run_input):
    for m in reversed(run_input.get("messages", [])):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def print_events(events, out=print):
    """Pretty-print an event stream for the terminal walkthrough, merging long ARGS runs."""
    pending = None
    for e in events:
        t = e["type"]
        if t in ("TEXT_MESSAGE_CONTENT", "TOOL_CALL_ARGS"):
            if pending and pending[0] == t:
                pending[1] += e["delta"]
                pending[2] += 1
                continue
            if pending:
                out(f"  {pending[0]:<22} x{pending[2]:<3} {pending[1][:110]!r}")
            pending = [t, e["delta"], 1]
            continue
        if pending:
            out(f"  {pending[0]:<22} x{pending[2]:<3} {pending[1][:110]!r}")
            pending = None
        rest = {k: v for k, v in e.items() if k != "type"}
        out(f"  {t:<22} {json.dumps(rest)[:140]}")
    if pending:
        out(f"  {pending[0]:<22} x{pending[2]:<3} {pending[1][:110]!r}")


def guarded(events, thread_id, run_id):
    """Pass events through; end with RUN_FINISHED unless a RUN_ERROR already ended the run."""
    for e in events:
        yield e
        if e["type"] == "RUN_ERROR":
            return
    yield run_finished(thread_id, run_id)
