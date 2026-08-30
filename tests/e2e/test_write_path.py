import uuid
from pathlib import Path
from scrum_team.runner import run_project_graph, get_project_state
from scrum_team.memory_store import get_memory, search_memory

def test_memory_write_path():
    proj_id = f"test-mem-{uuid.uuid4().hex[:6]}"
    print(f"--- TESTING MEMORY WRITE PATH FOR PROJECT: {proj_id} ---")
    
    # 1. Run pipeline until human review interrupt
    print("\n1. Running initial project phase...")
    run_project_graph(proj_id, raw_input="Build a CSV file cleaner in Python")
    
    # 2. Simulate human rejection with rework feedback
    print("\n2. Simulating human rejection (rework)...")
    run_project_graph(proj_id, resume_command={"approved": False, "feedback": "Add input validation for missing CSV columns"})
    
    # 3. Simulate human approval to trigger completion & memory extraction pass
    print("\n3. Simulating human approval (completion & extraction)...")
    run_project_graph(proj_id, resume_command={"approved": True})
    
    state = get_project_state(proj_id)
    print(f"Final status: {state.values.get('status')}")
    
    # 4. Verify memories written to store
    print("\n4. Inspecting stored memories in data/memory.db...")

    # Check project summary
    proj_summary = get_memory(("projects", proj_id, "summary"), "overview")
    print(f"Project Summary memory: {proj_summary.value if proj_summary else 'NOT FOUND'}")
    assert proj_summary is not None, "Project summary memory should be created"
    assert proj_summary.value["project_id"] == proj_id

    # Check developer code pattern
    dev_pattern = get_memory(("developer", "code_patterns"), f"pattern_{proj_id}")
    print(f"Developer Pattern memory: {dev_pattern.value if dev_pattern else 'NOT FOUND'}")
    assert dev_pattern is not None, "Developer pattern memory should be created"

    # Check rework lesson memory
    rework_mem = get_memory(("developer", "code_patterns"), f"rework_{proj_id}")
    print(f"Rework Lesson memory: {rework_mem.value if rework_mem else 'NOT FOUND'}")
    assert rework_mem is not None, "Rework lesson memory should be captured"

    # Check PO DoD preference
    po_mem = get_memory(("po", "dod_preferences"), "standard_dod")
    print(f"PO DoD memory: {po_mem.value if po_mem else 'NOT FOUND'}")
    assert po_mem is not None, "PO DoD memory should be created"

    # Check QA test pattern
    qa_mem = get_memory(("qa", "test_patterns"), "smoke_and_full_verification")
    print(f"QA Pattern memory: {qa_mem.value if qa_mem else 'NOT FOUND'}")
    assert qa_mem is not None, "QA test pattern memory should be created"

    print("\nALL MEMORY WRITE PATH CHECKS PASSED!")

if __name__ == "__main__":
    test_memory_write_path()
