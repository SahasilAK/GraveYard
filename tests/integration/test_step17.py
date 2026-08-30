import uuid
import os
from pathlib import Path
from scrum_team.utils.code_search import search_project_codebase
from scrum_team.nodes.dev_agent import conduct_task_research
from scrum_team.runner import run_project_graph, get_project_state

ROOT_DIR = Path(__file__).resolve().parent

def test_step17_developer_research():
    proj_id = f"test-step17-{uuid.uuid4().hex[:6]}"
    proj_path = ROOT_DIR / "projects" / proj_id
    proj_path.mkdir(parents=True, exist_ok=True)
    
    print(f"--- TESTING STEP 17 DEVELOPER RESEARCH LOOP ON PROJECT: {proj_id} ---")

    # 1. Create dummy existing files in project folder for search testing
    (proj_path / "auth_module.py").write_text("# Existing authentication logic\ndef authenticate_user(user, password):\n    return True\n", encoding="utf-8")
    (proj_path / "data_storage.py").write_text("# Existing storage logic\ndef save_data(payload):\n    pass\n", encoding="utf-8")

    # 2. Test scoped code search
    print("\n1. Testing scoped code search tool...")
    matches = search_project_codebase(proj_path, "authenticate")
    print(f"Code search matches for 'authenticate': {matches}")
    assert len(matches) > 0, "Code search should find 'authenticate' in auth_module.py"
    assert matches[0]["file"] == "auth_module.py"

    # Scoping check: verify search doesn't escape project path
    outside_matches = search_project_codebase(proj_path, "../scrum_team")
    assert len(outside_matches) == 0, "Code search must not match files outside project folder"

    # 3. Test hypothesis-driven, bounded research function
    print("\n2. Testing hypothesis-driven research sub-step...")
    sample_task = {
        "file_path": "auth_service.py",
        "logical_task": "Update existing auth_module authentication logic to support password hashing"
    }
    research_logs = conduct_task_research(sample_task, str(proj_path), max_steps=2)
    print(f"Research notes generated ({len(research_logs)} logs):")
    for r in research_logs:
        print(f"  - {r}")

    assert len(research_logs) <= 3, "Research steps must be bounded by max_steps"
    assert any("Searched" in r for r in research_logs), "Research should log search findings"

    # 4. End-to-end graph run test
    print("\n3. Testing end-to-end graph run with Developer research logging...")
    logs = []
    def logger(msg):
        logs.append(msg)
        print(f"[UI LOG] {msg}")

    run_project_graph(proj_id, raw_input="Add token-based authentication to existing auth module", log_callback=logger)
    
    state = get_project_state(proj_id)
    dev_out = state.values.get("dev_output", {})
    print(f"\nDeveloper Output: {dev_out}")
    
    assert "research_notes" in dev_out, "dev_output must include 'research_notes'"
    assert any("[Developer Research]" in l for l in logs), "Logs must contain Developer Research step events"

    # Clean up test files
    run_project_graph(proj_id, resume_command={"approved": True})
    
    print("\nALL STEP 17 DEVELOPER RESEARCH TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_step17_developer_research()
