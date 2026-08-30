import uuid
import pytest
from scrum_team.middleware.error_handler import execute_with_retry, safe_node_execution, GraphExecutionError
from scrum_team.runner import run_project_graph, get_project_state

def test_step20_error_handling_middleware():
    print("--- TESTING STEP 20 TOOL-CALL ERROR HANDLING MIDDLEWARE ---")
    
    logs = []
    def logger(msg):
        logs.append(msg)
        print(f"[UI LOG] {msg}")

    # 1. Test LLM retry logic on transient failure
    print("\n1. Testing execute_with_retry with simulated transient failure...")
    attempt_count = 0
    def flaky_llm_call():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise ConnectionError("Simulated OmniRoute connection timeout")
        return {"result": "success"}

    res = execute_with_retry(flaky_llm_call, max_retries=2, initial_delay=0.1, log_callback=logger, task_name="Test LLM Call")
    print(f"Retry Result: {res}")
    assert res == {"result": "success"}
    assert attempt_count == 2
    assert any("[Retry 1/2]" in l for l in logs)

    # 2. Test execute_with_retry unrecoverable failure
    print("\n2. Testing execute_with_retry unrecoverable failure handling...")
    def failing_llm_call():
        raise TimeoutError("Persistent OmniRoute endpoint timeout")

    try:
        execute_with_retry(failing_llm_call, max_retries=2, initial_delay=0.1, log_callback=logger, task_name="Persistent Failing Call")
        assert False, "Should raise GraphExecutionError"
    except GraphExecutionError as e:
        print(f"  - Successfully caught controlled error: {e}")
        assert "failed after 2 retries" in str(e)

    # 3. Test safe_node_execution middleware wrapper
    print("\n3. Testing safe_node_execution graph node wrapper...")
    def faulty_node(state):
        raise ValueError("Simulated unexpected node logic error")

    state_snapshot = {"project_id": "test-err-node", "status": "planning"}
    safe_res = safe_node_execution("faulty_node", faulty_node, state_snapshot, log_callback=logger)
    print(f"Safe Node Result: {safe_res}")
    assert safe_res["status"] == "error_paused"
    assert "faulty_node" in safe_res["error_node"]
    assert any("⚠️ [Node Error]" in l for l in logs)

    # 4. End-to-End pipeline sanity check
    print("\n4. Running end-to-end project workflow with error middleware...")
    proj_id = f"test-step20-{uuid.uuid4().hex[:6]}"
    run_project_graph(proj_id, raw_input="Create a resilient error logger module", log_callback=logger)
    
    state = get_project_state(proj_id)
    assert state.values.get("status") in ["qa_approval", "finished"], "Graph should complete safely without crashes"
    
    run_project_graph(proj_id, resume_command={"approved": True})
    print("\nALL STEP 20 ERROR HANDLING MIDDLEWARE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_step20_error_handling_middleware()
