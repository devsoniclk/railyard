"""
Example: Support ticket triage workflow.

Demonstrates guards that require escalation approval before a ticket
can be marked resolved.
"""

from railyard import Machine, Runtime, AgentAction, state


def build_machine() -> Machine:
    m = Machine(start="new")

    m.add(state("new", tools=["read_ticket", "classify"]))
    m.add(state("triaged", tools=["assign", "escalate"]))
    m.add(state("in_progress", tools=["reply", "escalate", "resolve"]))
    m.add(state("escalated", tools=["approve_escalation"]))
    m.add(state("resolved", terminal=True))

    m.allow("new -> triaged")
    m.allow("triaged -> in_progress")
    m.allow("triaged -> escalated")
    m.allow("in_progress -> escalated")
    m.allow("in_progress -> resolved", guard=lambda ctx: ctx.get("customer_confirmed", False))
    m.allow("escalated -> in_progress", guard=lambda ctx: ctx.get("escalation_approved", False))
    m.allow("escalated -> resolved", guard=lambda ctx: ctx.get("manager_override", False))

    m.validate()
    return m


def triage_agent(rt: Runtime, ctx: dict) -> AgentAction:
    """Deterministic demo agent."""
    s = rt.current_state

    if s == "new":
        return AgentAction("classify", "triaged", {"category": "billing"})
    if s == "triaged":
        return AgentAction("assign", "in_progress", {"assignee": "bob"})
    if s == "in_progress":
        return AgentAction("resolve", "resolved", {"note": "Refund issued"})
    raise RuntimeError(f"Unexpected state: {s}")


if __name__ == "__main__":
    from rich.console import Console

    console = Console()
    machine = build_machine()

    with machine.run(triage_agent) as session:
        while not session.is_terminal:
            action = session.step({"customer_confirmed": True})
            console.print(f"  {session.current_state} ← {action.tool}")

    console.print("[green]✓ Ticket resolved![/green]")
