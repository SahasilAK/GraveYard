# Step 24 — Real Developer Code Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Developer's hardcoded placeholder snippets with validated, structured LLM-generated source files, strengthen upstream task detail, and prove the prior CSV task produces runnable parsing code.

**Architecture:** Keep the existing LangGraph node and `write_code(plan_or_task, project_path)` interface, adding only optional generation dependencies for deterministic tests. The Developer will generate one complete file per planned `Task`, validate syntax and obvious placeholder markers before applying a replacement/creation diff, and retry invalid responses with the exact validation feedback. If generation remains invalid or explicitly blocked, it returns a failed result and writes nothing. The PO prompt and fallback will require implementation-ready AtomicTask descriptions; no graph topology change is needed.

**Tech Stack:** Python, Pydantic, LangChain `ChatOpenAI.with_structured_output`, existing `DiffTask`/path permissions, Python `ast`/`compile`, pytest.

**Spec:** Approved Step 24 requirements in the conversation; no separate specification file was requested.

## Global Constraints

- Preserve callers of `write_code(plan_or_task, project_path)` and existing result keys (`files_changed`, `summary`, `task_id`, `diff_results`, `research_notes`).
- Never write a placeholder, mock, pseudocode, TODO-only implementation, or print-only scaffolding when generation fails.
- Keep all file writes behind the existing `apply_diff_task` permission and project-path validation.
- Use a real LLM generation path in production and an injected/fake LLM only in tests; never require a live model endpoint for the CSV regression test.
- Do not change the LangGraph graph topology, persistence, or Streamlit UI for this step.
- Run the focused tests after each implementation slice, then run the full available test suite.

---

### Task 1: Add failing tests for real generation and the no-stub gate

**Files:**
- Create: `tests/unit/test_step24_developer.py`
- Modify: none

**Interfaces:**
- Tests will exercise `scrum_team.nodes.dev_agent.write_code`, `validate_generated_code`, and the optional `llm` injection described in later tasks.
- A fake structured-output model must expose `with_structured_output(schema)` and return an object with `code`, `status`, and `notes` attributes from `invoke(messages_or_prompt)`.

- [ ] **Step 1: Write the failing regression tests**

Add a fake model and tests with these exact behaviors:

```python
import ast
from pathlib import Path

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
            """import csv\n\ndef read_rows(path):\n    with open(path, newline=\"\", encoding=\"utf-8\") as handle:\n        return list(csv.DictReader(handle))\n"""
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
    csv_file.write_text("name,age\\nAda,36\\n", encoding="utf-8")
    assert namespace["read_rows"](csv_file) == [{"name": "Ada", "age": "36"}]


def test_invalid_placeholder_is_rejected_and_retried_without_writing_stub(tmp_path):
    llm = FakeLLM([
        generated("def read_rows(path):\n    print('Atomic step 1 executed.')\n"),
        generated("import csv\n\ndef read_rows(path):\n    with open(path, newline=\"\", encoding=\"utf-8\") as handle:\n        return list(csv.DictReader(handle))\n"),
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
```

The test also verifies the real behavior (the generated `read_rows` function parses an actual CSV file), not merely that the fake model was called.

- [ ] **Step 2: Run the focused tests and verify the expected RED state**

Run:

```bash
pytest tests/unit/test_step24_developer.py -q
```

Expected: collection or assertion failures because `GeneratedCode`, `llm=`, `max_generation_attempts=`, and `validate_generated_code` do not exist and the current implementation still writes its hardcoded `print` stub.

- [ ] **Step 3: Do not change production code in this task**

Leave the failing tests in place as the executable contract for the following tasks.

---

### Task 2: Implement structured Developer generation, validation, and retry

**Files:**
- Modify: `scrum_team/nodes/dev_agent.py`
- Modify: `scrum_team/common/entities.py`
- Test: `tests/unit/test_step24_developer.py`

**Interfaces:**
- Add `GeneratedCode(BaseModel)` to `scrum_team/common/entities.py` with `code: str`, `status: Literal["complete", "blocked"] = "complete"`, and `notes: str = ""`.
- Export/import it in `dev_agent.py` as `GeneratedCode` so tests and callers can use the same schema.
- Add `validate_generated_code(code: str, file_path: str) -> tuple[bool, str]`.
- Preserve `write_code(plan_or_task, project_path)` and extend it to `write_code(plan_or_task, project_path, llm=None, max_generation_attempts=3) -> dict`.
- Add `generate_file_code(task: dict, current_code: str, llm=None, max_attempts: int = 3) -> GeneratedCode` as the single generation/validation boundary.

- [ ] **Step 1: Define the strict Developer system prompt**

At module level, add `DEVELOPER_SYSTEM_PROMPT` containing all of the following intent verbatim in substance:

```text
You are the Developer agent. You must write complete, real, working implementation code that can run now. Never write placeholder functions, TODO or FIXME comments in place of logic, pseudocode, mock/stub implementations, or print statements that merely claim a step ran. Implement the requested behavior with real imports, real control flow, input handling, and error handling appropriate to the task. Return a complete source file, not a fragment.

BAD (forbidden):
def step_1_implementation():
    # Step 1: Import built-in CSV library and parse the file
    print('Atomic step 1 executed.')

GOOD (required for that task):
import csv

def read_rows(path):
    with open(path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))

If the task cannot be completed with the supplied information or depends on a missing module, set status to blocked and explain the missing information in notes. Never disguise incomplete work as source code. When status is complete, code must be syntactically valid and contain the requested behavior.
```

- [ ] **Step 2: Implement the validation gate before any write**

Use standard-library validation in `dev_agent.py`:

```python
import ast
import re

_PLACEHOLDER_MARKERS = (
    "atomic step",
    "feature implemented successfully",
    "todo",
    "fixme",
    "notimplementederror",
    "pseudocode",
)


def validate_generated_code(code: str, file_path: str) -> tuple[bool, str]:
    if not code or not code.strip():
        return False, "Generated code is empty."
    lowered = code.lower()
    for marker in _PLACEHOLDER_MARKERS:
        if marker in lowered:
            return False, f"Generated code contains a forbidden placeholder marker: {marker}."
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError as exc:
        return False, f"Generated code is not valid Python: {exc}."
    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            return False, "Generated code contains a placeholder pass statement."
    return True, ""
```

Keep this gate conservative and focused on the known failure mode; do not reject legitimate `print()` calls generally. The explicit prompt and marker checks reject the old print-only scaffold while allowing real programs that log output.

- [ ] **Step 3: Implement structured generation with corrective retry feedback**

Use the configured Developer model only when `llm` is omitted, and request `GeneratedCode` structured output:

```python
from langchain_core.messages import HumanMessage, SystemMessage
from scrum_team.common.entities import GeneratedCode
from scrum_team.utils.llm_factory import get_llm


def _generation_prompt(task, current_code, feedback=""):
    atomic_details = "\n".join(
        f"- {item.get('atomic_task', item) if isinstance(item, dict) else item}"
        f"\n  Context: {item.get('additional_context', '') if isinstance(item, dict) else ''}"
        for item in task.get("atomic_tasks", [])
    )
    return (
        f"Target file: {task.get('file_path', 'app.py')}\n"
        f"Overall task: {task.get('logical_task', '')}\n"
        f"Implementation requirements:\n{atomic_details}\n\n"
        f"Existing file contents (replace with a complete file; empty means create it):\n"
        f"```python\n{current_code}\n```\n"
        f"{feedback}"
    )


def generate_file_code(task, current_code, llm=None, max_attempts=3):
    structured_llm = (llm or get_llm("DEVELOPER")).with_structured_output(GeneratedCode)
    feedback = ""
    file_path = task.get("file_path", "app.py")
    for attempt in range(max_attempts):
        response = structured_llm.invoke([
            SystemMessage(content=DEVELOPER_SYSTEM_PROMPT),
            HumanMessage(content=_generation_prompt(task, current_code, feedback)),
        ])
        result = response if isinstance(response, GeneratedCode) else GeneratedCode.model_validate(response)
        if result.status == "blocked":
            raise ValueError(f"Developer marked task blocked: {result.notes or 'missing requirements'}")
        valid, error = validate_generated_code(result.code, file_path)
        if valid:
            return result
        feedback = (
            "\nVALIDATION FEEDBACK FROM THE DEVELOPER PIPELINE: " + error
            + " Correct the source and return the entire complete file; do not return a stub.\n"
        )
    raise ValueError(f"Generated code failed validation after {max_attempts} attempts: {feedback.strip()}")
```

Use a clear error when `max_attempts < 1`. Preserve the actual validation reason so the retry prompt and final result are actionable.

- [ ] **Step 4: Replace hardcoded scaffolding in `write_code`**

In the structured-plan branch, for each task:

1. Run `conduct_task_research` as before.
2. Normalize the target path to `.py` as existing behavior does.
3. Read the current file if it exists; otherwise use `""`.
4. Call `generate_file_code` with the task and current content.
5. Apply one `DiffTask` whose `original_code_snippet` is the full current content and whose `new_code_snippet` is the generated complete file. For a missing file, use an empty original snippet so `apply_diff_task` creates it.
6. Append the result. Add the relative file path to `files_created` only on success.
7. If generation raises, append `{"success": False, "error": str(exc), "file_path": fpath}` and continue/return the normal result; do not call `apply_diff_task` with generated fallback text.

In the plain-task fallback branch, remove the hardcoded `print('Feature implemented successfully.')`. Convert the plain task into a concrete task dictionary and use the same generation boundary. If the model cannot generate a complete file, return a failed diff result and leave the project unchanged.

Remove the duplicate imports and duplicate `conduct_task_research` definition while touching this file; keep one implementation and one `MAX_RESEARCH_STEPS` constant.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run:

```bash
pytest tests/unit/test_step24_developer.py -q
```

Expected: all Step 24 Developer tests pass, including actual execution of the generated CSV parser and the no-write-on-final-failure assertion.

---

### Task 3: Make upstream plans implementation-ready

**Files:**
- Modify: `scrum_team/nodes/po_agent.py`
- Modify: `scrum_team/common/entities.py`
- Modify: `tests/integration/test_step16.py`
- Test: `tests/unit/test_step24_developer.py` (add prompt assertion)

**Interfaces:**
- Keep `generate_plan_from_backlog(backlog_item: dict) -> Plan` unchanged.
- Keep `AtomicTask.atomic_task: str` and `AtomicTask.additional_context: Optional[str]` compatible with existing serialized state.

- [ ] **Step 1: Add a failing prompt-quality assertion**

Extend the fake-model tests with a fake PO LLM (or monkeypatch `scrum_team.nodes.po_agent.get_llm`) and assert the plan-generation prompt contains requirements for:

```python
assert "inputs" in prompt.lower()
assert "outputs" in prompt.lower()
assert "function signature" in prompt.lower() or "signature" in prompt.lower()
assert "example" in prompt.lower()
assert "edge cases" in prompt.lower()
```

Also add an assertion in the existing structured-contract integration test that the first atomic task's text is not the vague fallback label and that either `additional_context` is present or the task text includes concrete input/output detail.

- [ ] **Step 2: Run the prompt-quality tests and verify RED**

Run:

```bash
pytest tests/unit/test_step24_developer.py tests/integration/test_step16.py -q
```

Expected: the new prompt assertions fail against the current short PO prompt/fallback.

- [ ] **Step 3: Strengthen the PO plan-generation prompt**

Update `generate_plan_from_backlog`'s prompt to require:

- one file area per `Task`;
- each `AtomicTask` to name the concrete function/class or exact code area;
- expected inputs and outputs/types;
- normal and edge-case behavior;
- at least one concrete example or acceptance check;
- required imports/dependencies when relevant;
- no labels such as “implement the feature,” “add support,” or “import library” without behavior.

State that `additional_context` must carry examples, constraints, and integration assumptions that do not fit in `atomic_task`.

- [ ] **Step 4: Make the fallback plan concrete**

Replace the fallback `"Implement the core feature"` with a description derived from the backlog item, for example:

```python
fallback_description = str(backlog_item.get("description", "")).strip()
fallback_criteria = "; ".join(backlog_item.get("acceptance_criteria", []))
AtomicTask(
    atomic_task=(
        f"Implement the requested behavior for '{backlog_item.get('title', 'feature')}' "
        f"in {backlog_item.get('id', 'TASK-1')}. Define the public function or entry point, "
        f"accept the inputs described below, return the requested output, and handle invalid "
        f"or empty input without placeholder logic. Description: {fallback_description}"
    ),
    additional_context=(
        f"Acceptance criteria: {fallback_criteria}. "
        "If a function signature is not specified, choose and document a small callable "
        "signature that directly satisfies the description."
    ),
)
```

Ensure the fallback remains a valid `Plan` and never promises behavior unavailable from the backlog; its concrete uncertainty must be visible in `additional_context`.

- [ ] **Step 5: Update model field descriptions**

Make `AtomicTask` field descriptions explicitly require implementation detail, e.g. `atomic_task` must describe behavior rather than a label and `additional_context` should include inputs, outputs, examples, edge cases, and dependencies when applicable. Do not add unnecessary schema fields.

- [ ] **Step 6: Run prompt and contract tests and verify GREEN**

Run:

```bash
pytest tests/unit/test_step24_developer.py tests/integration/test_step16.py -q
```

Expected: prompt-quality and structured-contract tests pass. If the integration test requires the configured local model service and cannot run in this environment, report that exact external failure instead of weakening the assertions.

---

### Task 4: Run the complete regression suite and verify the graph contract

**Files:**
- Modify: none unless a test exposes an incompatibility in the Step 24 code
- Test: `tests/unit/test_step24_developer.py`, existing `tests/**/*.py`

**Interfaces:**
- The existing graph still calls `write_code(plan_dict, project_path)` without changes to `scrum_team/graph.py`.
- Developer output keeps `files_changed`, `diff_results`, `research_notes`, and `task_id` so `runner.py` logging remains compatible.

- [ ] **Step 1: Run Python compilation checks**

Run:

```bash
python -m py_compile scrum_team/common/entities.py scrum_team/nodes/dev_agent.py scrum_team/nodes/po_agent.py
```

Expected: no output and exit code 0.

- [ ] **Step 2: Run the complete test suite**

Run:

```bash
pytest -q
```

Expected: all deterministic unit/integration tests pass. Any live-model or environment-dependent failure must be reported with its output and not hidden.

- [ ] **Step 3: Inspect the generated-code path for forbidden scaffolding**

Run:

```bash
python -c "from pathlib import Path; p=Path('scrum_team/nodes/dev_agent.py'); s=p.read_text(encoding='utf-8'); assert \"Atomic step {idx+1} executed.\" not in s; assert \"Feature implemented successfully.\" not in s"
```

Expected: exit code 0.

- [ ] **Step 4: Report completion accurately**

Report the files changed, focused CSV behavior, validation/retry behavior, and exact test results. Do not claim the full suite passes if an external model service is unavailable.
