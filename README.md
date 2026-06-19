# 🚂 Railyard

**State-machine guardrails for AI agents.**

> Prompts beg the agent not to deploy without approval. A state machine makes it impossible.

---

## The Problem

LLM agents fail in predictable ways:

| Bug Class | Example | Railyard Fix |
|-----------|---------|-------------|
| **Infinite loop** | Agent retries forever | Terminal states are enforced |
| **Skipped step** | Agent jumps draft → done | Transitions must be declared |
| **Early deploy** | Agent deploys before review | Guard requires approval flag |
| **Early exit** | Agent stops mid-workflow | Non-terminal states have outgoing edges |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    STATE MACHINE                     │
│                                                     │
│  ┌────────┐    ┌──────────┐    ┌──────────┐         │
│  │ draft  │───▶│  review  │───▶│ approved │──┐      │
│  └────────┘    └──────────┘    └──────────┘  │      │
│    tools:       tools:         tools:        ▼      │
│    write,       comment,       deploy     ┌──────┐  │
│    edit         approve                   │ done │  │
│                  ▲                        └──────┘  │
│                  │ guard:                          │
│                  │ tests_passed=True               │
│  ┌───────────────┘                                 │
│  │                                                 │
│  └─────────────────────────────────────────────────│
│                                                     │
│  RUNTIME                                            │
│  • Filters tools per state                          │
│  • Validates transitions before executing           │
│  • Logs every transition to JSONL                   │
└─────────────────────────────────────────────────────┘
```

---

## Quickstart

```bash
pip install -e .
```

### Define a deploy-gating machine

```python
from railyard import Machine, state, AgentAction

m = Machine(start="draft")

m.add(state("draft", tools=["write", "edit"]))
m.add(state("review", tools=["comment", "request_changes", "approve"]))
m.add(state("approved", tools=["deploy"]))
m.add(state("done", terminal=True))

m.allow("draft -> review")
m.allow("review -> approved", guard=lambda ctx: ctx.get("tests_passed", False))
m.allow("approved -> done")

m.validate()
```

### Run an agent through it

```python
def my_agent(rt, ctx):
    """The runtime filters tools — agent only sees what's legal."""
    if rt.current_state == "draft":
        return AgentAction(tool="edit", next_state="review")
    if rt.current_state == "review":
        return AgentAction(tool="approve", next_state="approved")
    if rt.current_state == "approved":
        return AgentAction(tool="deploy", next_state="done")

with m.run(my_agent) as session:
    actions = session.run_until_done(context={"tests_passed": True})
    # Agent physically cannot deploy from 'draft' state
```

### What happens on an illegal move?

```python
def rogue_agent(rt, ctx):
    return AgentAction(tool="deploy", next_state="done")  # skip review!

with m.run(rogue_agent) as session:
    session.step()
    # → InvalidTransition: Tool 'deploy' not allowed in state 'draft'
```

---

## Replay & Audit Trail

Every transition is logged as JSONL:

```python
# After a run, inspect the log
for entry in session._runtime.log:
    print(f"{entry['from']} → {entry['to']} ({entry['action']})")

# Save to disk
session._runtime.log.save("audit.jsonl")

# Replay and verify
from railyard import TransitionLog, Replay

log = TransitionLog.load("audit.jsonl")
result = Replay(m).check(log)
print(result.valid)      # True if all transitions were legal
print(result.errors)     # Details of any violations
```

---

## CLI

```bash
railyard validate machine.yaml    # check a machine definition
railyard replay audit.jsonl       # replay a transition log
```

---

## Examples

- [`examples/code_review_deploy.py`](examples/code_review_deploy.py) — 4-state deploy workflow
- [`examples/support_triage.py`](examples/support_triage.py) — ticket triage with escalation

---

## Roadmap

- [ ] YAML machine loader (`railyard.load("machine.yaml")`)
- [ ] LangChain adapter (auto-filter Tool objects)
- [ ] CrewAI adapter
- [ ] Visual state graph renderer (DOT/SVG)
- [ ] Prometheus metrics for transitions
- [ ] Distributed log (Redis/Postgres backend)
- [ ] `railyard init` scaffolding command

---

## License

[MIT](LICENSE)
