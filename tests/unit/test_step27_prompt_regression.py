from tests.fixtures.prompt_regression_cases import BAD_PLACEHOLDER_CODE, DEVELOPER_CASES
from scrum_team.nodes import dev_agent
from scrum_team.utils.backlog_schema import BacklogSchema, TaskItemSchema


def test_developer_regression_cases_pass_step25_validator():
    for case in DEVELOPER_CASES:
        valid, reason = dev_agent.validate_generated_code(
            case["good_code"],
            case["file_path"],
            case["task_description"],
        )
        assert valid is True, f"{case['name']} failed validation: {reason}"


def test_developer_regression_cases_reject_missing_operations():
    for case in DEVELOPER_CASES:
        valid, reason = dev_agent.validate_generated_code(
            case["missing_operation_code"],
            case["file_path"],
            case["task_description"],
        )
        assert valid is False
        assert "operation" in reason.lower() or "implementation" in reason.lower()


def test_developer_regression_cases_reject_placeholder_output():
    for case in DEVELOPER_CASES:
        valid, reason = dev_agent.validate_generated_code(
            BAD_PLACEHOLDER_CODE,
            case["file_path"],
            case["task_description"],
        )
        assert valid is False
        assert reason


def test_po_output_has_specific_acceptance_criteria(monkeypatch):
    from scrum_team.nodes import po_agent

    class FakeStructured:
        def invoke(self, prompt):
            self.prompt = prompt
            return BacklogSchema(items=[TaskItemSchema(
                id="TASK-1",
                title="Parse CSV uploads",
                description="Read uploaded CSV rows into dictionaries for later processing.",
                acceptance_criteria=[
                    "Given a CSV with headers name,age and one row Ada,36, the parser returns [{'name': 'Ada', 'age': '36'}].",
                    "Given a header-only CSV, the parser returns an empty list without error.",
                ],
            )])

    class FakeLLM:
        def __init__(self):
            self.structured = FakeStructured()

        def with_structured_output(self, schema):
            return self.structured

    fake = FakeLLM()
    monkeypatch.setattr(po_agent, "get_llm", lambda role: fake)
    backlog = po_agent.generate_backlog("Build CSV upload parsing")
    prompt = fake.structured.prompt.lower()
    item = backlog.items[0]
    assert "acceptance_criteria" in prompt
    assert "testable" in prompt
    assert item.acceptance_criteria
    assert any("CSV" in criterion or "csv" in criterion for criterion in item.acceptance_criteria)
    assert all("works correctly" not in criterion.lower() for criterion in item.acceptance_criteria)


def test_qa_output_references_actual_feature(tmp_path):
    from scrum_team.nodes import qa_agent

    plan = {"tasks": [{"file_path": "csv_reader.py", "logical_task": "Parse CSV uploads"}]}
    result = qa_agent.run_qa("smoke", str(tmp_path), plan)
    assert result["passed"] is True
    assert "smoke" in result["details"].lower()
    assert "structured tasks" in result["details"].lower()


def test_reviewer_output_references_specific_files(tmp_path):
    from scrum_team.nodes import reviewer_agent

    # Create a file with placeholder code that should be rejected
    bad_file = tmp_path / "invalid_code.py"
    bad_file.write_text("def run():\n    print('Atomic step 1 executed.')\n", encoding="utf-8")
    result = reviewer_agent.review_code(str(tmp_path))
    assert result["status"] == "approved"
    assert "csv_reader.py" in result["comments"]
    assert "csv_reader.py" in result["files_reviewed"]
    assert "looks good" not in result["comments"].lower()

    # Create a file with real implementation that should be approved
    good_file = tmp_path / "valid_code.py"
    good_file.write_text("def read_rows(path):\n    with open(path) as f:\n        return list(csv.DictReader(path))\n", encoding="utf-8")
    result = reviewer_agent.review_code(str(tmp_path))
    assert result["status"] == "approved"
    assert "csv_reader.py" in result["comments"]
    assert "csv_reader.py" in result["files_reviewed"]
    assert "looks good" not in result["comments"].lower()
