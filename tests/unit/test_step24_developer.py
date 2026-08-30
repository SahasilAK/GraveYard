import ast

from scrum_team.nodes import dev_agent


class FakeStructuredModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return next(self.responses)


class FakeLLM:
    def __init__(self, responses):
        self.structured = FakeStructuredModel(responses)

    def with_structured_output(self, schema):
        return self.structured


def generated(code, status="complete", notes=""):
    return dev_agent.GeneratedCode(code=code, status=status, notes=notes)


def test_csv_task_writes_real_parsing_code(tmp_path):
    llm = FakeLLM([
        generated(
            """import csv

def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
"""
        )
    ])
    plan = {
        "tasks": [{
            "file_path": "csv_reader.py",
            "logical_task": "Read CSV records into dictionaries",
            "atomic_tasks": [{
                "atomic_task": "Define read_rows(path) accepting a filesystem path and returning one dictionary per CSV data row using csv.DictReader; preserve headers and support a header-only file.",
                "additional_context": "Example input: name,age\\nAda,36\\n; expected output: [{'name': 'Ada', 'age': '36'}].",
            }],
        }]
    }

    result = dev_agent.write_code(plan, str(tmp_path), llm=llm)
    output = tmp_path / "csv_reader.py"
    assert result["diff_results"][0]["success"] is True
    assert output.exists()
    source = output.read_text(encoding="utf-8")
    ast.parse(source)
    assert "csv.DictReader" in source
    namespace = {}
    exec(compile(source, str(output), "exec"), namespace)
    csv_file = tmp_path / "records.csv"
    csv_file.write_text("name,age\nAda,36\n", encoding="utf-8")
    assert namespace["read_rows"](csv_file) == [{"name": "Ada", "age": "36"}]


def test_invalid_placeholder_is_rejected_and_retried_without_writing_stub(tmp_path):
    llm = FakeLLM([
        generated("def read_rows(path):\n    print('Atomic step 1 executed.')\n"),
        generated("""import csv

def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
"""),
    ])
    plan = {"tasks": [{
        "file_path": "csv_reader.py",
        "logical_task": "Read CSV records",
        "atomic_tasks": [{"atomic_task": "Implement read_rows(path) with csv.DictReader."}],
    }]}

    result = dev_agent.write_code(plan, str(tmp_path), llm=llm, max_generation_attempts=2)
    source = (tmp_path / "csv_reader.py").read_text(encoding="utf-8")
    assert result["diff_results"][-1]["success"] is True
    assert "Atomic step" not in source
    assert len(llm.structured.prompts) == 2
    assert "validation" in str(llm.structured.prompts[1]).lower()


def test_po_prompt_requires_implementation_details(monkeypatch):
    from scrum_team.nodes import po_agent

    class FakeStructured:
        def invoke(self, prompt):
            self.prompt = prompt
            return {"tasks": []}

    class FakePO:
        def __init__(self):
            self.structured = FakeStructured()

        def with_structured_output(self, schema):
            return self.structured

    fake = FakePO()
    monkeypatch.setattr(po_agent, "get_llm", lambda role: fake)
    po_agent.generate_plan_from_backlog({"title": "Read CSV", "description": "Parse records", "acceptance_criteria": ["returns rows"]})
    prompt = fake.structured.prompt.lower()
    assert "inputs" in prompt
    assert "outputs" in prompt
    assert "signature" in prompt
    assert "example" in prompt
    assert "edge-case" in prompt


def test_generation_failure_does_not_create_a_fake_file(tmp_path):
    llm = FakeLLM([
        generated("def read_rows(path):\n    print('Atomic step 1 executed.')\n"),
    ])
    plan = {"tasks": [{
        "file_path": "csv_reader.py",
        "logical_task": "Read CSV records",
        "atomic_tasks": [{"atomic_task": "Implement read_rows(path) with csv.DictReader."}],
    }]}

    result = dev_agent.write_code(plan, str(tmp_path), llm=llm, max_generation_attempts=1)
    assert result["diff_results"][0]["success"] is False
    assert not (tmp_path / "csv_reader.py").exists()
    assert "placeholder" in result["diff_results"][0]["error"].lower()
