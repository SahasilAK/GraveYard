import uuid
from scrum_team.runner import run_project_graph, get_project_state

def test_full_ui_backend_flow():
    logs = []
    def ui_logger(msg):
        logs.append(msg)
        print(f"[UI LOG] {msg}")

    proj_id = f"test-ui-proj-{uuid.uuid4().hex[:6]}"
    print(f"\n==========================================")
    print(f"TESTING END-TO-END WORKFLOW: {proj_id}")
    print(f"==========================================")

    # 1. New Project submission
    print("\n--- 1. Submitting New Project Request ---")
    run_project_graph(proj_id, raw_input="Create a task manager CLI tool in Python", log_callback=ui_logger)

    state = get_project_state(proj_id)
    assert "human_review" in state.next, f"Expected interrupt at human_review, got {state.next}"
    print(f"STATUS AFTER RUN 1: {state.values.get('status')} | NEXT: {state.next}")

    # 2. Reject with feedback (Rework loop)
    print("\n--- 2. Submitting Human Review Rejection (Rework) ---")
    run_project_graph(proj_id, resume_command={"approved": False, "feedback": "Add JSON storage support"}, log_callback=ui_logger)

    state2 = get_project_state(proj_id)
    assert "human_review" in state2.next, f"Expected interrupt at human_review after rework, got {state2.next}"
    print(f"STATUS AFTER REWORK: {state2.values.get('status')} | NEXT: {state2.next}")

    # 3. Approve
    print("\n--- 3. Submitting Human Review Approval ---")
    run_project_graph(proj_id, resume_command={"approved": True}, log_callback=ui_logger)

    state3 = get_project_state(proj_id)
    assert state3.values.get("status") == "finished", f"Expected status 'finished', got {state3.values.get('status')}"
    print(f"FINAL STATUS: {state3.values.get('status')}")
    print(f"TOTAL LOGS CAPTURED: {len(logs)}")
    print("==========================================\nSUCCESS!")

if __name__ == "__main__":
    test_full_ui_backend_flow()
