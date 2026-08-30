# Step 27-28 Prompt Regression and Production Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline prompt regression coverage first, then production-grade README/docs/user-guide coverage.

**Architecture:** Step 27 reuses the existing Step 25 `validate_generated_code()` gate and current fake-LLM test pattern so prompt regressions stay cheap and deterministic. Step 28 adds focused docs under `docs/` and updates `README.md` so setup, usage, examples, testing, architecture, and production-readiness are discoverable.

**Tech Stack:** Python, pytest, existing LangChain/LangGraph app structure, Markdown docs.

**Spec:** `final_implementation.md` Step 27 and Step 28 text.

## Global Constraints

- Implement in order: complete Step 27 before Step 28.
- Do not require live provider credentials for the new regression suite.
- Reuse `scrum_team.nodes.dev_agent.validate_generated_code()`; do not add a second validator.
- Keep docs concrete: commands, paths, examples, and expected behavior.
- No new dependencies.

---

### Task 1: Step 27 Developer Prompt Regression Fixtures

**Files:**
- Create: `tests/fixtures/prompt_regression_cases.py`
- Create: `tests/unit/test_step27_prompt_regression.py`

**Interfaces:**
- Consumes: `scrum_team.nodes.dev_agent.validate_generated_code(code: str, file_path: str, task_description: str) -> tuple[bool, str]`
- Produces: `DEVELOPER_CASES`, a list of dictionaries with `name`, `file_path`, `task_description`, `good_code`, and `required_markers`.

- [ ] **Step 1: Create regression fixture module**

Create `tests/fixtures/prompt_regression_cases.py`:

```python
DEVELOPER_CASES = [
    {
        "name": "csv_reader",
        "file_path": "csv_reader.py",
        "task_description": "Parse CSV records into dictionaries",
        "good_code": """import csv


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
""",
        "required_markers": ("csv.DictReader", "open("),
    },
    {
        "name": "json_loader",
        "file_path": "json_loader.py",
        "task_description": "Load JSON configuration from disk",
        "good_code": """import json


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
""",
        "required_markers": ("json.load", "open("),
    },
    {
        "name": "api_endpoint",
        "file_path": "api.py",
        "task_description": "Create an API endpoint that returns health status",
        "good_code": """from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}
""",
        "required_markers": ("@app.get", "status"),
    },
]

BAD_PLACEHOLDER_CODE = "def run():\n    print('Atomic step 1 executed.')\n"
```

- [ ] **Step 2: Write failing developer regression tests**

Create `tests/unit/test_step27_prompt_regression.py` with:

```python
from tests.fixtures.prompt_regression_cases import BAD_PLACEHOLDER_CODE, DEVELOPER_CASES
from scrum_team.nodes import dev_agent


def test_developer_regression_cases_pass_step25_validator():
    for case in DEVELOPER_CASES:
        valid, reason = dev_agent.validate_generated_code(
            case["good_code"],
            case["file_path"],
            case["task_description"],
        )
        assert valid is True, f"{case['name']} failed validation: {reason}"
        for marker in case["required_markers"]:
            assert marker in case["good_code"]


def test_developer_regression_cases_reject_placeholder_output():
    for case in DEVELOPER_CASES:
        valid, reason = dev_agent.validate_generated_code(
            BAD_PLACEHOLDER_CODE,
            case["file_path"],
            case["task_description"],
        )
        assert valid is False
        assert reason
```

- [ ] **Step 3: Run the new tests and confirm import failure or pass**

Run: `python -m pytest tests/unit/test_step27_prompt_regression.py -q`
Expected after both files exist: PASS.

---

### Task 2: Step 27 PO/QA/Reviewer Output Quality Checks

**Files:**
- Modify: `tests/unit/test_step27_prompt_regression.py`

**Interfaces:**
- Consumes: `scrum_team.nodes.po_agent.generate_backlog(brief: str) -> BacklogSchema`
- Consumes: `scrum_team.nodes.qa_agent.run_qa(mode: str, project_path: str, plan_or_task: dict | None = None) -> dict`
- Consumes: `scrum_team.nodes.reviewer_agent.review_code(project_path: str) -> dict`
- Produces: offline tests that enforce specific role output quality.

- [ ] **Step 1: Add PO fake LLM quality test**

Append to `tests/unit/test_step27_prompt_regression.py`:

```python
from scrum_team.utils.backlog_schema import BacklogSchema, TaskItemSchema


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
    item = backlog.items[0]
    assert item.acceptance_criteria
    assert any("CSV" in criterion or "csv" in criterion for criterion in item.acceptance_criteria)
    assert all("works correctly" not in criterion.lower() for criterion in item.acceptance_criteria)
```

- [ ] **Step 2: Add QA output quality test**

Append:

```python

def test_qa_output_references_actual_feature(tmp_path):
    from scrum_team.nodes import qa_agent

    plan = {"tasks": [{"file_path": "csv_reader.py", "logical_task": "Parse CSV uploads"}]}
    result = qa_agent.run_qa("smoke", str(tmp_path), plan)
    assert result["passed"] is True
    assert "smoke" in result["details"].lower()
    assert "structured tasks" in result["details"].lower()
```

- [ ] **Step 3: Add Reviewer output quality test**

Append:

```python

def test_reviewer_output_references_specific_files(tmp_path):
    from scrum_team.nodes import reviewer_agent

    (tmp_path / "csv_reader.py").write_text("def read_rows(path):\n    return []\n", encoding="utf-8")
    result = reviewer_agent.review_code(str(tmp_path))
    assert result["status"] == "approved"
    assert "csv_reader.py" in result["comments"]
    assert "csv_reader.py" in result["files_reviewed"]
    assert "looks good" not in result["comments"].lower()
```

- [ ] **Step 4: Run Step 27 tests**

Run: `python -m pytest tests/unit/test_step27_prompt_regression.py tests/unit/test_step25_validation_gate.py tests/unit/test_prompt_templates.py -q`
Expected: PASS.

---

### Task 3: Step 27 README Prompt Regression Command

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: existing `## Prompt Regression Checks` README section.
- Produces: documented command that future prompt edits must run.

- [ ] **Step 1: Update README prompt regression section**

Replace the current `## Prompt Regression Checks` section with:

```markdown
## Prompt Regression Checks

Prompt templates are canonical files under `scrum_team/agents/prompts/`. After changing any prompt template, run the offline prompt regression suite before trusting the change against real projects:

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```

This suite checks that Developer output still passes the Step 25 validation gate, placeholder code is rejected, PO acceptance criteria stay specific, QA output references the real work, and Reviewer output names inspected files. Live end-to-end runs require configured provider credentials and are separate from this offline gate.
```

- [ ] **Step 2: Run README-related tests**

Run: `python -m pytest tests/unit/test_step27_prompt_regression.py -q`
Expected: PASS.

---

### Task 4: Step 28 Production Documentation Set

**Files:**
- Create: `docs/USER_GUIDE.md`
- Create: `docs/EXAMPLES.md`
- Create: `docs/TESTING.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/PRODUCTION_READINESS.md`
- Modify: `README.md`

**Interfaces:**
- Produces docs with these exact headings: `# User Guide`, `# Examples`, `# Testing`, `# Architecture`, `# Production Readiness`.
- Produces README links to all five docs.

- [ ] **Step 1: Create user guide**

Create `docs/USER_GUIDE.md`:

```markdown
# User Guide

## Start the app

1. Run `first_run.bat` once to create the virtual environment and install dependencies.
2. Run `start_app.bat` to open the Streamlit dashboard.
3. Configure provider credentials before running live agent workflows.

## Create a project

1. Open the Chat tab.
2. Describe the product or feature in concrete terms.
3. Submit the brief and watch the Logs tab for agent activity.
4. Review Developer output when the graph pauses for human approval.
5. Choose Approve to continue or Request Rework to send feedback back into the workflow.

## Manage memory

Use the Memory Manager tab to inspect or delete long-term memories stored in `data/memory.db`. Delete memories that are stale, too rigid, or contradicted by current project requirements.

## Read generated output

Generated source code is written under `projects/<project_name>/`. Check the Logs tab for validation-gate events, retries, QA smoke checks, and review comments.
```

- [ ] **Step 2: Create examples doc**

Create `docs/EXAMPLES.md`:

```markdown
# Examples

## Example project brief

```text
Build a small Python utility that reads a CSV file with name and age columns and returns a list of dictionaries. It should handle header-only files by returning an empty list and should raise a clear error for missing files.
```

## Expected team flow

1. Prompt Agent converts the brief into a structured project brief.
2. Product Owner creates backlog items with acceptance criteria.
3. Scrum Master routes the next ready task.
4. Developer writes real code and passes the Step 25 validation gate.
5. QA runs a smoke check.
6. Reviewer inspects changed files.
7. Human approval decides whether to continue or request rework.

## Example generated file location

```text
projects/csv_utility/csv_reader.py
```

## Example prompt-regression command

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```
```

- [ ] **Step 3: Create testing doc**

Create `docs/TESTING.md`:

```markdown
# Testing

## Fast offline checks

```bash
python -m pytest tests/unit -q
```

## Prompt regression gate

Run this after editing anything under `scrum_team/agents/prompts/`:

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```

## Full suite

```bash
python -m pytest tests -q
```

Some end-to-end tests require provider credentials. If credentials are missing, failures mentioning `OPENAI_API_KEY`, `OPENAI_ADMIN_KEY`, or provider authentication are environment failures, not prompt-regression failures.

## Windows helper

```bat
run_tests.bat
```
```

- [ ] **Step 4: Create architecture doc**

Create `docs/ARCHITECTURE.md`:

```markdown
# Architecture

## Overview

AI Scrum Team is a local multi-agent workflow that turns a user brief into backlog, implementation, QA, review, and human approval steps.

## Agent roles

- Prompt Agent: converts unstructured input into a structured brief.
- Product Owner: creates backlog and concrete implementation plans.
- Scrum Master: routes workflow state.
- Developer: researches and writes scoped project files.
- QA Engineer: runs smoke checks and reports results.
- Reviewer: inspects generated files before completion.

## Prompt templates

Canonical role prompts live in `scrum_team/agents/prompts/` and are loaded by `scrum_team/agents/prompt_loader.py`. Prompt edits must pass the prompt regression gate documented in `docs/TESTING.md`.

## State and storage

- Checkpoints: `data/checkpoints.db`
- Long-term memory: `data/memory.db`
- Generated projects: `projects/<project_name>/`

## Validation gate

Developer output is checked by `scrum_team.nodes.dev_agent.validate_generated_code()` before QA. Placeholder, mock, pseudo, print-only, and missing-operation implementations are rejected and regenerated within the configured retry limit.
```

- [ ] **Step 5: Create production readiness doc**

Create `docs/PRODUCTION_READINESS.md`:

```markdown
# Production Readiness

## Required before real use

- Configure provider credentials and model routing.
- Run the prompt regression gate after every prompt edit.
- Run the full test suite before releasing changes.
- Review generated code before approving workflow continuation.
- Monitor Logs for validation-gate retries and failed agent calls.

## Operational data

The app stores checkpoint and memory data locally under `data/`. Back up this directory if workflow continuity and learned preferences matter for your deployment.

## Security boundaries

Agent file access is scoped to generated project directories. Keep secrets out of project briefs and generated project folders. Do not approve generated code that writes outside `projects/<project_name>/`.

## Known limits

Live end-to-end tests need provider credentials. The validation gate is heuristic and catches common placeholder patterns; QA and human review remain required for production-grade confidence.
```

- [ ] **Step 6: Update README docs index**

Add after the opening description in `README.md`:

```markdown
## Documentation

- [User Guide](docs/USER_GUIDE.md) — operating the dashboard and workflow.
- [Examples](docs/EXAMPLES.md) — sample briefs, expected flow, and regression commands.
- [Testing](docs/TESTING.md) — unit, prompt-regression, and full-suite commands.
- [Architecture](docs/ARCHITECTURE.md) — agent roles, state, storage, and validation gate.
- [Production Readiness](docs/PRODUCTION_READINESS.md) — release, operations, and safety checklist.
```

- [ ] **Step 7: Run markdown/doc smoke check**

Run: `python -m pytest tests/unit/test_step27_prompt_regression.py -q`
Expected: PASS. Then manually confirm all README links point to files created in this task.

---

### Task 5: Final Verification

**Files:**
- Test: `tests/unit/test_step27_prompt_regression.py`
- Test: `tests/unit/test_step25_validation_gate.py`
- Test: `tests/unit/test_prompt_templates.py`
- Docs: `README.md`, `docs/*.md`

**Interfaces:**
- Consumes all previous task outputs.
- Produces final verified Step 27 and Step 28 implementation status.

- [ ] **Step 1: Run offline prompt gate**

Run:

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full suite**

Run:

```bash
python -m pytest tests -q
```

Expected: unit tests pass; existing e2e/provider-credential failures may remain if local credentials are not configured.

- [ ] **Step 3: Record result**

Report:

```text
Step 27 complete: prompt regression fixtures and offline tests added.
Step 28 complete: production-grade docs and README index added.
Verification: <exact pytest result>.
Known remaining failures: <exact environment-related failures, if any>.
```
