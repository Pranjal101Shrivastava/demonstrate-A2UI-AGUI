"""A tiny agent HARNESS: the model <-> tools loop, with UI as just another tool.

    while True:
        reply = model(messages, tools)            # text, or tool calls
        if no tool calls: break
        for call in tool calls:
            result = TOOLS[call.name](**call.input) # validated; errors become results
            messages.append(tool_result)

Rendering tools (show_component / render_ui / render_html) do not return data
to the model; they put pixels on SURFACES: a terminal renderer and, through
AG-UI events, a web page. Every loop callback becomes an AG-UI event, so the
same harness drives both surfaces.

Scripted mode: a `policy(messages)` function plays the model deterministically.
Live mode (GENUX_LIVE=1): Claude drives the loop with real tool use.
"""
import json
import os

from common import agui

MAX_STEPS = 8


class ToolError(Exception):
    """Raised by a tool for bad input; returned to the model as is_error=True."""


class Harness:
    def __init__(self, system, tools, policy, surfaces=()):
        self.system, self.tools, self.policy = system, tools, policy  # tools: name -> (schema, fn)
        self.surfaces = list(surfaces)  # callables receiving ("render", payload)
        self.messages = []

    # ---- the model step: scripted policy or Claude
    def model_step(self):
        if os.environ.get("GENUX_LIVE") == "1" and os.environ.get("ANTHROPIC_API_KEY"):
            return self._claude_step()
        return self.policy(self.messages)

    def _claude_step(self):
        import anthropic

        client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=os.environ.get("GENUX_MODEL", "claude-opus-5-5"), max_tokens=16000, system=self.system,
            messages=self.messages, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            tools=[{"name": n, "description": s["description"], "input_schema": s["input_schema"]} for n, (s, _) in self.tools.items()],
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("model refused")
        content = [b.model_dump(exclude_none=True) for b in resp.content]  # pass every block back unchanged
        return {"content": content}

    # ---- the loop; yields AG-UI events
    def run(self, user_text, thread="harness", run_id="run"):
        self.messages.append({"role": "user", "content": user_text})
        yield agui.run_started(thread, run_id)
        for step in range(1, MAX_STEPS + 1):
            reply = self.model_step()
            self.messages.append({"role": "assistant", "content": reply["content"]})
            calls = [b for b in reply["content"] if b["type"] == "tool_use"]
            for b in reply["content"]:
                if b["type"] == "text" and b["text"].strip():
                    yield from agui.text_message(b["text"], lambda s: [s])
            if not calls:
                break
            results = []
            for call in calls:
                yield {"type": "TOOL_CALL_START", "toolCallId": call["id"], "toolCallName": call["name"]}
                yield {"type": "TOOL_CALL_ARGS", "toolCallId": call["id"], "delta": json.dumps(call["input"])}
                yield {"type": "TOOL_CALL_END", "toolCallId": call["id"]}
                try:
                    if call["name"] not in self.tools:
                        raise ToolError(f"unknown tool {call['name']}")
                    out = self.tools[call["name"]][1](**call["input"])
                    render = out.pop("_render", None) if isinstance(out, dict) else None
                    if render:
                        for s in self.surfaces:
                            s(render)
                        yield agui.custom("render", render)  # the web surface draws this
                    content, err = json.dumps(out), False
                except (ToolError, TypeError) as e:
                    content, err = f"ERROR: {e}", True
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": content, **({"is_error": True} if err else {})})
                yield {"type": "TOOL_CALL_RESULT", "messageId": agui.new_id("msg"), "toolCallId": call["id"], "role": "tool", "content": content}
            self.messages.append({"role": "user", "content": results})  # all results in ONE user message
        yield agui.run_finished(thread, run_id)


def tool_use(name, inp, i=[0]):
    """Helper for scripted policies: build an assistant tool_use block."""
    i[0] += 1
    return {"type": "tool_use", "id": f"toolu_{i[0]:03}", "name": name, "input": inp}


def text(t):
    return {"type": "text", "text": t}


def last_results(messages):
    """The tool_result blocks the policy is reacting to (or [] after a plain user turn)."""
    m = messages[-1]
    return m["content"] if isinstance(m["content"], list) else []


def steps_since_user(messages):
    """How many assistant turns happened since the last plain-text user message."""
    n = 0
    for m in reversed(messages):
        if m["role"] == "user" and isinstance(m["content"], str):
            break
        n += m["role"] == "assistant"
    return n


def result_json(messages, k=0):
    """Parse the k-th tool_result of the latest tool-result message."""
    return json.loads(last_results(messages)[k]["content"])
