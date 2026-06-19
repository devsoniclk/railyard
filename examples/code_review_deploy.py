"""
Example: Code review → deploy workflow.

Demonstrates a 4-state machine that gates deployment behind an explicit
approval step.
"""

from railyard import Machine, Runtime, AgentAction, state


def build_machine() -> Machine:
    m = Machine(start="draft")

    m.add(state("draft", tools=["write", "edit"]))
    m.add(state("review", tools=["comment", "request_changes", "approve"]))
    m.add(state("approved", tools=["deploy"]))
    m.add(state("done", terminal=True))

    m.allow("draft -> review")
    m.allow("review -> draft")  # send back for changes
    m.allow(
        "review -> approved",
        guard=lambda ctx: ctx.get("tests_passed", False),
    )
    m.allow("approved -> done")

    m.validate()
    return m


# -- a pretend agent -------------------------------------------------------

def code_review_agent(rt: Runtime, ctx: dict) -> AgentAction:
    """
    A deterministic agent for demonstration.

    In a real system this would be an LLM call; here we just walk the
    happy path.
    """
    state = rt.current_state
    allowed = rt.allowed_tools

    if state == "draft":
        return AgentAction(tool="edit", next_state="review", payload={"pr": 42})

    if state == "review":
        # Pretend tests passed
        return AgentAction(
            tool="approve", next_state="approved", payload={"reviewer": "alice"}
        )

    if state == "approved":
        return AgentAction(
            tool="deploy", next_state="done", payload={"target": "prod"}
        )

    raise RuntimeError(f"Unexpected state: {state}")


# -- main ------------------------------------------------------------------

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    machine = build_machine()

    table = Table(title="Code Review → Deploy Machine")
    table.add_column("State")
    table.add_column("Tools")
    table.add_column("Terminal")
    for s in machine.states:
        table.add_row(s.name, ", ".join(s.tools), str(s.terminal))
    console.print(table)

    with machine.run(code_review_agent) as session:
        while not session.is_terminal:
            action = session.step({"tests_passed": True})
            console.print(
                f"  [bold]{session.current_state}[/bold] ← {action.tool} "
                f"({action.payload})"
            )

    console.print("\n[green]✓ Reached terminal state![/green]")
    console.print(f"Transition log ({len(machine.run(code_review_agent)._runtime.log)} entries):")
