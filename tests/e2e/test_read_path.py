import uuid
from scrum_team.runner import run_project_graph, get_project_state
from scrum_team.memory_store import get_memory, put_memory

def test_memory_read_path():
    proj_a = f"test-read-a-{uuid.uuid4().hex[:6]}"
    proj_b = f"test-read-b-{uuid.uuid4().hex[:6]}"
    
    print("==================================================")
    print("TESTING MEMORY READ PATH & CONTEXT INJECTION")
    print("==================================================")
    
    # 1. Run Project A to completion to seed cross-project memories
    print(f"\n1. Seeding memory via Project A ({proj_a})...")
    run_project_graph(proj_a, raw_input="Create a JSON parser CLI tool")
    run_project_graph(proj_a, resume_command={"approved": True})
    
    # Check that Project A saved memories
    summary_a = get_memory(("projects", proj_a, "summary"), "overview")
    print(f"Project A summary in memory: {summary_a.value if summary_a else 'NONE'}")
    assert summary_a is not None, "Project A summary should exist in memory"

    # 2. Run Project B and observe memory retrieval & context injection
    print(f"\n2. Executing Project B ({proj_b}) with memory retrieval...")
    logs_b = []
    def logger_b(msg):
        logs_b.append(msg)
        print(f"[UI LOG B] {msg}")

    run_project_graph(proj_b, raw_input="Create a YAML to JSON converter CLI tool", log_callback=logger_b)
    
    state_b = get_project_state(proj_b)
    brief_b = state_b.values.get("brief", "")
    print(f"\nProject B Brief: {brief_b[:200]}...")

    # Check generated dev output file for Project B
    dev_out = state_b.values.get("dev_output", {})
    print(f"Project B Dev Output: {dev_out}")
    
    # Check logs for memory retrieval indicators
    retrieval_logs = [l for l in logs_b if "memory" in l.lower() or "retrieved" in l.lower() or "applied" in l.lower()]
    print(f"\nLogs indicating memory retrieval: {retrieval_logs}")
    assert len(retrieval_logs) > 0, "Logs should record memory retrieval events for Project B"

    # Clean finish Project B
    run_project_graph(proj_b, resume_command={"approved": True})
    
    print("\nALL MEMORY READ PATH & RETRIEVAL CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_memory_read_path()
