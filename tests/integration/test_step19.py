import uuid
import pytest
from pathlib import Path
from scrum_team.tools.permissions import check_agent_tool_permission, validate_project_path, read_project_file_scoped
from scrum_team.utils.code_search import search_project_codebase
from scrum_team.utils.diff_applier import apply_diff_task
from scrum_team.common.entities import DiffTask
from scrum_team.nodes.qa_agent import run_qa

ROOT_DIR = Path(__file__).resolve().parent

def test_step19_tool_curation_and_scoping():
    proj_id = f"test-step19-{uuid.uuid4().hex[:6]}"
    proj_path = ROOT_DIR / "projects" / proj_id
    proj_path.mkdir(parents=True, exist_ok=True)
    
    (proj_path / "index.py").write_text("print('scoped content')", encoding="utf-8")

    print(f"--- TESTING STEP 19 TOOL CURATION & PERMISSIONS ON PROJECT: {proj_id} ---")

    # 1. Test unauthorized agent tool calls
    print("\n1. Testing unauthorized agent tool access...")
    try:
        check_agent_tool_permission("PROMPT_AGENT", "read_project_file")
        assert False, "Prompt Agent must not have read_project_file permission"
    except PermissionError as e:
        print(f"  - Correctly blocked Prompt Agent: {e}")

    try:
        check_agent_tool_permission("QA_ENGINEER", "apply_diff")
        assert False, "QA Engineer must not have apply_diff permission"
    except PermissionError as e:
        print(f"  - Correctly blocked QA Engineer write tool: {e}")

    try:
        check_agent_tool_permission("REVIEWER", "write_project_file")
        assert False, "Reviewer must not have write_project_file permission"
    except PermissionError as e:
        print(f"  - Correctly blocked Reviewer write tool: {e}")

    # 2. Test authorized agent tool calls
    print("\n2. Testing authorized agent tool access...")
    content = read_project_file_scoped("index.py", proj_path, agent_role="DEVELOPER")
    assert "scoped content" in content, "Developer should be able to read scoped file"

    qa_res = run_qa("smoke", str(proj_path))
    assert qa_res["passed"] is True, "QA Engineer should run smoke test"

    # 3. Test path isolation boundary (preventing traversal outside projects/<project_name>/)
    print("\n3. Testing path isolation boundary enforcement...")
    outside_rel = "../scrum_team/graph.py"
    
    try:
        validate_project_path(outside_rel, proj_path)
        assert False, "Path traversal outside project directory must be blocked"
    except PermissionError as e:
        print(f"  - Correctly blocked path traversal: {e}")

    try:
        read_project_file_scoped(outside_rel, proj_path, agent_role="DEVELOPER")
        assert False, "Reading file outside project directory must be blocked"
    except PermissionError as e:
        print(f"  - Correctly blocked out-of-bounds file read: {e}")

    illegal_diff = DiffTask(
        file_path="../unauthorized_target.py",
        original_code_snippet="",
        task_description="Illegal write attempt",
        new_code_snippet="bad = True"
    )
    diff_res = apply_diff_task(illegal_diff, proj_path, agent_role="DEVELOPER")
    assert diff_res["success"] is False, "DiffTask to outside path must fail"
    assert "scoping violation" in diff_res["error"].lower()

    print("\nALL STEP 19 TOOL PERMISSION & SCOPING CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_step19_tool_curation_and_scoping()
