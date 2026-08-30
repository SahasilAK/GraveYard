from scrum_team.agents.prompt_loader import load_prompt
from scrum_team.nodes import dev_agent, qa_agent, reviewer_agent


def test_canonical_prompts_improve_role_specific_quality():
    old_po = "Decompose project brief into prioritized tasks."
    new_po = load_prompt("PO")
    assert "acceptance_criteria" not in old_po
    assert "acceptance_criteria" in new_po
    assert "testable" in new_po.lower()

    qa = qa_agent.run_qa("smoke", ".")
    assert qa["passed"] is True
    assert "smoke" in qa["details"].lower()
    assert "." in qa["details"]

    review = reviewer_agent.review_code(".")
    assert review["files_reviewed"]
    assert "inspected" in review["comments"].lower() or "review" in review["comments"].lower()
    assert len(review["comments"].split()) >= 8


def test_developer_prompt_and_validator_require_real_csv_logic():
    assert "never" in dev_agent.DEVELOPER_SYSTEM_PROMPT.lower()
    code = "import csv\n\ndef parse_csv(path):\n    with open(path, newline='', encoding='utf-8') as handle:\n        return list(csv.DictReader(handle))\n"
    assert dev_agent.validate_generated_code(code, "csv_reader.py", "Parse CSV records") == (True, "")
