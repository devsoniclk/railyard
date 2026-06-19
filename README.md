# Railyard

Prompts tell agents what not to do. State machines make certain things impossible.

The problem with prompt-based guardrails is that they're suggestions. "Don't deploy before tests pass" is a polite request. Railyard enforces it structurally — the `deploy` tool simply doesn't exist until the machine is in the `approved` state.

```bash
pip install -e .
```

## How it works

You define a state machine. Each state exposes only the tools valid in that state. Transitions between states are declared explicitly, with optional guard conditions. The agent runs through the runtime, which enforces the machine at every step.

```python
from railyard import Machine, state, AgentAction

m = Machine(start="draft")

m.add(state("draft",    tools=["write", "edit"]))
m.add(state("review",   tools=["comment", "request_changes", "approve"]))
m.add(state("approved", tools=["deploy"]))
m.add(state("done",     terminal=True))

m.allow("draft -> review")
m.allow("review -> approved", guard=lambda ctx: ctx.get("tests_passed", False))
m.allow("approved -> done")

m.validate()
```

The `validate()` call checks that every non-terminal state has at least one outgoing transition, and that no state is unreachable. Catches structural bugs in your machine definition before runtime.

Running an agent through it:

```python
def my_agent(rt, ctx):
    if rt.current_state == "draft":
        return AgentAction(tool="edit", next_state="review")
    if rt.current_state == "review":
        return AgentAction(tool="approve", next_state="approved")
    if rt.current_state == "approved":
        return AgentAction(tool="deploy", next_state="done")

with m.run(my_agent) as session:
    session.run_until_done(context={"tests_passed": True})
```

If the agent tries to skip a step:

```python
def rogue_agent(rt, ctx):
    return AgentAction(tool="deploy", next_state="done")  # from draft state

with m.run(rogue_agent) as session:
    session.step()
    # InvalidTransition: Tool 'deploy' not allowed in state 'draft'
```

It doesn't return an error to the agent. It raises. The agent can't recover from it by trying something else.

## Audit trail

Every transition is logged as JSONL:

```python
session._runtime.log.save("audit.jsonl")

from railyard import TransitionLog, Replay
log = TransitionLog.load("audit.jsonl")
result = Replay(m).check(log)
print(result.valid)   # did every transition follow the declared machine?
print(result.errors)  # details if not
```

## CLI

```bash
railyard validate machine.yaml
railyard replay audit.jsonl
```

## Examples

- [`examples/code_review_deploy.py`](examples/code_review_deploy.py) — 4-state deploy workflow with test gate
- [`examples/support_triage.py`](examples/support_triage.py) — ticket routing with escalation path

## What's missing

YAML machine loader is on the list. Right now you define machines in Python. LangChain and CrewAI adapters aren't done either — the core runtime is framework-agnostic but the integrations that filter tool lists automatically are still manual.

## License

MIT
