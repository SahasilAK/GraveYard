import uuid
import os
from pathlib import Path
from scrum_team.common.entities import DiffTask
from scrum_team.utils.diff_applier import apply_diff_task
from scrum_team.runner import run_project_graph, get_project_state

ROOT_DIR = Path(__file__).resolve().parent

def test_step18_atomic_diff_generation():
    proj_id = f"test-step18-{uuid.uuid4().hex[:6]}"
    proj_path = ROOT_DIR / "projects" / proj_id
    proj_path.mkdir(parents=True, exist_ok=True)
    
    print(f"--- TESTING STEP 18 ATOMIC DIFF-BASED CODE GENERATION ON PROJECT: {proj_id} ---")

    # 1. Test creation of new file via DiffTask
    print("\n1. Testing creation of a new file via DiffTask...")
    new_file_diff = DiffTask(
        file_path="utils/helper.py",
        original_code_snippet="",
        task_description="Create helper utility file",
        new_code_snippet="def initial_helper():\n    return 'initial'\n"
    )
    res_create = apply_diff_task(new_file_diff, proj_path)
    print(f"Creation Result: {res_create}")
    assert res_create["success"] is True, "Creation via DiffTask should succeed"
    assert res_create["action"] == "created_file"
    assert (proj_path / "utils" / "helper.py").exists()

    # 2. Test targeted replacement in existing file
    print("\n2. Testing targeted replacement in existing file...")
    replace_diff = DiffTask(
        file_path="utils/helper.py",
        original_code_snippet="def initial_helper():\n    return 'initial'",
        task_description="Update initial_helper function return value",
        new_code_snippet="def initial_helper():\n    return 'updated_atomic_diff'"
    )
    res_replace = apply_diff_task(replace_diff, proj_path)
    print(f"Replacement Result: {res_replace}")
    assert res_replace["success"] is True, "Targeted snippet replacement should succeed"
    assert "updated_atomic_diff" in (proj_path / "utils" / "helper.py").read_text(encoding="utf-8")

    # 3. Test snippet mismatch error handling (does not corrupt file)
    print("\n3. Testing error handling for non-existent snippet mismatch...")
    mismatch_diff = DiffTask(
        file_path="utils/helper.py",
        original_code_snippet="def non_existent_function():\n    pass",
        task_description="Attempt invalid snippet replacement",
        new_code_snippet="def replaced(): pass"
    )
    res_mismatch = apply_diff_task(mismatch_diff, proj_path)
    print(f"Mismatch Result: {res_mismatch}")
    assert res_mismatch["success"] is False, "Snippet mismatch should fail safely"
    assert "not found" in res_mismatch["error"].lower()

    # 4. Test path scoping isolation boundary
    print("\n4. Testing path scoping isolation boundary...")
    outside_diff = DiffTask(
        file_path="../outside_secret.py",
        original_code_snippet="",
        task_description="Attempt illegal path write",
        new_code_snippet="secret = True"
    )
    res_outside = apply_diff_task(outside_diff, proj_path)
    print(f"Outside Path Result: {res_outside}")
    assert res_outside["success"] is False, "Path outside project folder must be blocked"
    assert "scoping violation" in res_outside["error"].lower()

    # 5. End-to-End Graph Run
    print("\n5. Testing end-to-end graph run with atomic diff generation...")
    logs = []
    def logger(msg):
        logs.append(msg)
        print(f"[UI LOG] {msg}")

    run_project_graph(proj_id, raw_input="Create a string formatter module in Python with helper functions", log_callback=logger)
    
    state = get_project_state(proj_id)
    dev_out = state.values.get("dev_output", {})
    print(f"\nDeveloper Output: {dev_out}")
    
    assert "diff_results" in dev_out, "dev_output must include 'diff_results'"
    assert len(dev_out["diff_results"]) > 0, "Developer should return atomic diff results"

    # Clean finish
    run_project_graph(proj_id, resume_command={"approved": True})

    print("\nALL STEP 18 ATOMIC DIFF TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_step18_atomic_diff_generation()
