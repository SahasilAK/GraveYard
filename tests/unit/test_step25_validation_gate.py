from scrum_team.nodes import dev_agent


class FakePlan:
    def model_dump(self):
        return {"tasks": [{"file_path": "TASK-1.py", "logical_task": "Parse CSV", "atomic_tasks": []}]}


def test_validator_rejects_not_implemented_stub():
    valid, reason = dev_agent.validate_generated_code(
        "def parse_csv(path):\n    raise NotImplementedError('later')\n",
        "csv_reader.py",
        "Parse CSV records",
    )

    assert valid is False
    assert "notimplemented" in reason.lower() or "not implemented" in reason.lower()


def test_validator_accepts_real_csv_parser():
    valid, reason = dev_agent.validate_generated_code(
        "import csv\n\ndef parse_csv(path):\n    with open(path, newline='', encoding='utf-8') as handle:\n        return list(csv.DictReader(handle))\n",
        "csv_reader.py",
        "Parse CSV records",
    )

    assert valid is True
    assert reason == ""


def test_validator_rejects_csv_task_without_csv_operation():
    valid, reason = dev_agent.validate_generated_code(
        "def parse_csv(path):\n    return []\n",
        "csv_reader.py",
        "Parse CSV records",
    )

    assert valid is False
    assert "csv" in reason.lower()


def test_validator_rejects_import_only_csv_stub():
    valid, reason = dev_agent.validate_generated_code(
        "import csv\n\ndef parse_csv(path):\n    return []\n",
        "csv_reader.py",
        "Parse CSV records",
    )

    assert valid is False
    assert "operation" in reason.lower() or "implementation" in reason.lower()


def test_generation_result_preserves_validation_events():
    class FakeStructured:
        def __init__(self):
            self.calls = 0

        def invoke(self, _prompt):
            self.calls += 1
            if self.calls == 1:
                return dev_agent.GeneratedCode(code="def parse_csv(path):\n    return []\n")
            return dev_agent.GeneratedCode(
                code="import csv\n\ndef parse_csv(path):\n    with open(path, newline='', encoding='utf-8') as handle:\n        return list(csv.DictReader(handle))\n"
            )

    class FakeLLM:
        structured = FakeStructured()

        def with_structured_output(self, _schema):
            return self.structured

    result = dev_agent.generate_file_code(
        {"file_path": "csv_reader.py", "logical_task": "Parse CSV records"},
        "",
        llm=FakeLLM(),
        max_attempts=2,
    )

    assert result.validation_events
    assert "rejected" in result.validation_events[0].lower()


def test_dev_node_does_not_route_invalid_output_to_qa(monkeypatch):
    from scrum_team import graph

    monkeypatch.setattr(graph, "generate_plan_from_backlog", lambda task: FakePlan())
    monkeypatch.setattr(graph, "write_code", lambda plan, path: {
        "files_changed": [],
        "task_id": "TASK-1",
        "diff_results": [{"success": False, "error": "Generated code contains placeholder logic."}],
        "validation_events": ["[Validation Gate] rejected TASK-1.py: placeholder logic"],
    })

    result = graph.dev_agent_node({
        "backlog": [{"id": "TASK-1", "title": "Parse CSV"}],
        "completed_task_ids": [],
        "task_status_map": {},
        "project_id": "demo",
    })

    assert result["status"] == "failed"
    assert result["dev_output"]["validation_events"]
