import uuid
from langgraph.types import Command
from scrum_team.graph import create_graph

def test_hitl_loop():
    graph = create_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"--- STARTING RUN: {thread_id} ---")

    # 1. Start execution — runs until interrupt
    initial_state = {"project_id": thread_id, "raw_input": "Fix the gym tracker bug."}
    print("\n--- Initial Run (runs up to the human-review interrupt) ---")
    for event in graph.stream(initial_state, config=config, stream_mode="updates"):
        print(event)

    # 2. Check graph is paused at human_review
    state = graph.get_state(config)
    print(f"\n--- Paused at: {state.next}")

    # 3. REJECT — provide feedback, expect rework loop
    print("\n--- SIMULATING REJECTION ---")
    for event in graph.stream(
        Command(resume={"approved": False, "feedback": "Fix the gym tracker bug, it's really slow."}),
        config=config, stream_mode="updates"
    ):
        print(event)

    state2 = graph.get_state(config)
    print(f"\n--- Paused at (rework): {state2.next}")

    # 4. APPROVE — expect full QA and completion
    print("\n--- SIMULATING APPROVAL ---")
    for event in graph.stream(
        Command(resume={"approved": True}),
        config=config, stream_mode="updates"
    ):
        print(event)

    final = graph.get_state(config)
    print(f"\n--- FINAL STATUS: {final.values.get('status')} ---")

if __name__ == "__main__":
    test_hitl_loop()
