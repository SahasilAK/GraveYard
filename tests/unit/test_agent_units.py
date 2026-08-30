import pytest
from scrum_team.nodes.prompt_agent import generate_brief
from scrum_team.common.entities import DiffTask, Plan, Task, AtomicTask
from scrum_team.utils.diff_applier import apply_diff_task

def test_prompt_agent_logic():
    raw_input = "Make a simple todo list app in Python using Flask"
    brief = generate_brief(raw_input)
    assert brief is not None
    assert hasattr(brief, "goal")
    assert "Flask" in brief.goal or "todo" in brief.goal.lower() or "Flask" in str(brief.scope)

def test_diff_task_logic(tmp_path):
    proj_dir = tmp_path / "test_proj"
    proj_dir.mkdir()
    diff = DiffTask(
        file_path="main.py",
        original_code_snippet="",
        task_description="Create main entry",
        new_code_snippet="print('Hello World')\n"
    )
    res = apply_diff_task(diff, proj_dir)
    assert res["success"] is True
    assert (proj_dir / "main.py").read_text(encoding="utf-8") == "print('Hello World')\n"
