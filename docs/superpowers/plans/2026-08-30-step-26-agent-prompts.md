# Step 26 Agent Prompt Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace scattered generic agent instructions with six concise, auditable expert prompt templates and verify that each role produces its required structured, specific output.

**Architecture:** Store one Markdown template per role under `scrum_team/agents/prompts/`. A small loader reads templates by stable role key and caches them, while each node prepends the loaded template to its existing task-specific context. Existing Pydantic schemas and workflow behavior remain unchanged; deterministic fake-model tests exercise prompt loading and role quality without requiring API credentials.

**Tech Stack:** Python 3.10+, Pydantic, LangChain message/structured-output interfaces, pytest, Markdown prompt templates.

**Spec:** Approved Step 26 design in the conversation and `final_implementation.md:3-4`.

## Global Constraints

- Every template must contain exactly these headings: `## Persona`, `## Scope`, `## Output Format`, and `## Hard Constraints`.
- Templates must be concise, explicitly state responsibilities and exclusions, and include a minimal valid example.
- Preserve existing schemas and public node function signatures.
- Do not add a runtime LLM call or a new dependency for prompt loading.
- Never make live credentials a prerequisite for prompt regression tests.

---

### Task 1: Add the canonical prompt templates and loader

**Files:**
- Create: `scrum_team/agents/__init__.py`
- Create: `scrum_team/agents/prompts/__init__.py`
- Create: `scrum_team/agents/prompts/prompt_agent.md`
- Create: `scrum_team/agents/prompts/product_owner.md`
- Create: `scrum_team/agents/prompts/scrum_master.md`
- Create: `scrum_team/agents/prompts/developer.md`
- Create: `scrum_team/agents/prompts/qa_engineer.md`
- Create: `scrum_team/agents/prompts/reviewer.md`
- Create: `scrum_team/agents/prompt_loader.py`
- Test: `tests/unit/test_prompt_templates.py`

**Interfaces:**
- Produces `load_prompt(role: str) -> str` and `PROMPT_FILES: dict[str, str]`.
- Role keys are `PROMPT_AGENT`, `PO`, `SCRUM_MASTER`, `DEVELOPER`, `QA_ENGINEER`, and `REVIEWER`.
- `load_prompt` raises `KeyError` for an unknown role and `FileNotFoundError` if a canonical file is missing.

- [ ] **Step 1: Write the failing tests**

```python
from scrum_team.agents.prompt_loader import load_prompt


def test_every_role_has_the_same_required_sections():
    for role in ("PROMPT_AGENT", "PO", "SCRUM_MASTER", "DEVELOPER", "QA_ENGINEER", "REVIEWER"):
        prompt = load_prompt(role)
        assert all(section in prompt for section in ("## Persona", "## Scope", "## Output Format", "## Hard Constraints"))
        assert "Example" in prompt


def test_loader_rejects_unknown_roles():
    try:
        load_prompt("UNKNOWN")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown roles must fail")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/unit/test_prompt_templates.py`
Expected: FAIL because `scrum_team.agents.prompt_loader` and canonical files do not exist.

- [ ] **Step 3: Add the loader and six templates**

Implement `prompt_loader.py` using `Path(__file__).parent / "prompts"`, a role-to-filename mapping, and `read_text(encoding="utf-8")`; do not embed prompt text in Python. Each Markdown file must use the shared headings and contain these role-specific contracts:

- Prompt Agent: output `BriefSchema` with `goal`, `scope`, `constraints`, `acceptance_criteria`, and `priorities`; no file access; never invent requirements.
- PO: output `BacklogSchema` or `Plan`; backlog items include testable acceptance criteria, and plan tasks use `Task(file_path, logical_task, atomic_tasks)` with `AtomicTask(atomic_task, additional_context)`; no implementation.
- Scrum Master: output routing/state decisions only; use statuses `planning`, `qa_smoke`, `qa_approval`, `full_qa`, `finished`, or `failed`; no product or code changes.
- Developer: output `GeneratedCode` and implementation-compatible `DiffTask`; complete runnable source; no placeholders, mocks, pseudocode, or print-only stubs.
- QA: output `{passed: bool, details: str}`; inspect the project and run the smoke check before approval; no writes.
- Reviewer: output `{status: "approved"|"flagged", comments: str, files_reviewed: list[str]}`; inspect actual files and cite concrete findings; no uninspected approvals.

Every template must include one minimal valid example matching its stated contract.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/unit/test_prompt_templates.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrum_team/agents tests/unit/test_prompt_templates.py
git commit -m "feat: add canonical expert agent prompts"
```

### Task 2: Wire Prompt Agent, PO, and Scrum Master to canonical prompts

**Files:**
- Modify: `scrum_team/nodes/prompt_agent.py`
- Modify: `scrum_team/nodes/po_agent.py`
- Modify: `scrum_team/graph.py`
- Test: `tests/unit/test_prompt_templates.py`

**Interfaces:**
- Existing `generate_brief`, `generate_backlog`, `generate_plan_from_backlog`, and graph routing signatures remain unchanged.
- Prompt-bearing LLM calls must include `load_prompt("PROMPT_AGENT")`, `load_prompt("PO")`, or `load_prompt("SCRUM_MASTER")` as the stable system instruction.

- [ ] **Step 1: Add failing wiring assertions**

Extend the test with fake structured LLMs that capture prompts and assert the captured prompt contains the matching persona and required output model name (`BriefSchema`, `BacklogSchema`, or `Plan`). Add a graph-router test asserting the Scrum Master template is exposed through a named `SCRUM_MASTER_SYSTEM_PROMPT` constant or equivalent loader call.

- [ ] **Step 2: Run the focused tests**

Run: `.venv/Scripts/python.exe -m pytest -q tests/unit/test_prompt_templates.py`
Expected: FAIL because these nodes still use inline generic instructions and the graph has no Scrum Master prompt.

- [ ] **Step 3: Replace inline instructions with loaded templates**

Load the relevant template once at module scope (or through a module helper), then compose the existing request/brief text after it. Keep memory context and truncation behavior unchanged. Add a concise `SCRUM_MASTER_SYSTEM_PROMPT = load_prompt("SCRUM_MASTER")` constant in `graph.py`; preserve the router’s deterministic logic and use the constant only as the canonical prompt source for future/observability use, without introducing an unnecessary LLM call.

- [ ] **Step 4: Run focused and existing agent tests**

Run: `.venv/Scripts/python.exe -m pytest -q tests/unit/test_prompt_templates.py tests/unit/test_agent_units.py tests/unit/test_step24_developer.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrum_team/nodes/prompt_agent.py scrum_team/nodes/po_agent.py scrum_team/graph.py tests/unit/test_prompt_templates.py
git commit -m "refactor: use canonical planning agent prompts"
```

### Task 3: Wire Developer, QA, and Reviewer prompts without changing contracts

**Files:**
- Modify: `scrum_team/nodes/dev_agent.py`
- Modify: `scrum_team/nodes/qa_agent.py`
- Modify: `scrum_team/nodes/reviewer_agent.py`
- Test: `tests/unit/test_prompt_templates.py`
- Test: `tests/unit/test_step24_developer.py`

**Interfaces:**
- `generate_file_code` continues returning `GeneratedCode`; validation and `validation_events` behavior from Step25 remains intact.
- `run_qa` continues returning `dict` with `passed` and `details`.
- `review_code` continues returning `dict` with `status`, `comments`, and `files_reviewed`.

- [ ] **Step 1: Add failing prompt-content assertions**

Assert `dev_agent.DEVELOPER_SYSTEM_PROMPT == load_prompt("DEVELOPER")` (or equivalent loaded content), and add fake LLM tests that capture QA/reviewer prompt inputs and require role-specific terms: smoke execution and actual feature references for QA; inspected files, concrete findings, and approval gate for Reviewer.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/unit/test_prompt_templates.py tests/unit/test_step24_developer.py`
Expected: FAIL because Developer uses the old inline prompt and QA/Reviewer do not use LLM prompts.

- [ ] **Step 3: Wire canonical templates**

Replace `DEVELOPER_SYSTEM_PROMPT` text with `load_prompt("DEVELOPER")`; retain all Step25 validation logic. For QA and Reviewer, use the loaded templates as the role contract in the existing deterministic functions and include concrete project path/target details in returned `details`/`comments`; do not add network calls or fabricate test execution. If the current deterministic implementation cannot perform a real smoke check, return `passed=False` with the reason rather than claim success.

- [ ] **Step 4: Run focused tests**

Run: `.venv/Scripts/python.exe -m pytest -q tests/unit/test_prompt_templates.py tests/unit/test_step24_developer.py tests/unit/test_step25_validation_gate.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scrum_team/nodes/dev_agent.py scrum_team/nodes/qa_agent.py scrum_team/nodes/reviewer_agent.py tests/unit/test_prompt_templates.py tests/unit/test_step24_developer.py
git commit -m "refactor: apply expert prompts to execution agents"
```

### Task 4: Add deterministic end-to-end prompt-quality regression coverage

**Files:**
- Create: `tests/e2e/test_step26_prompt_quality.py`
- Modify: `README.md`

**Interfaces:**
- Tests use local fake structured models and existing schemas; no API key or external service.
- Quality assertions cover PO acceptance criteria, QA feature specificity, Reviewer inspection depth, and Developer non-placeholder output.

- [ ] **Step 1: Write the failing quality tests**

Create fixed sample tasks for CSV parsing, an HTTP endpoint, and a bug fix. Capture prompts passed to each role and assert:

```python
assert all(item["acceptance_criteria"] for item in backlog)
assert all(len(criteria) >= 2 and any(word in " ".join(criteria).lower() for word in ("input", "output", "error", "when")) for criteria in backlog)
assert "smoke" in qa_details.lower() and "csv" in qa_details.lower()
assert len(reviewer_comments.split()) >= 12 and any(name in reviewer_comments for name in files_reviewed)
assert dev_agent.validate_generated_code(generated_code, "csv_reader.py", "Parse CSV") == (True, "")
```

Include before/after prompt fixtures: the old generic prompt should fail at least one specificity assertion, while the canonical prompt fixture passes all assertions. Keep fixture outputs synthetic and deterministic.

- [ ] **Step 2: Run the quality test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest -q tests/e2e/test_step26_prompt_quality.py`
Expected: FAIL before wiring/quality behavior is complete.

- [ ] **Step 3: Implement only the minimum fixture adapters and documentation**

Use the existing node entry points and fake models; do not alter production workflow solely to satisfy test wording. Document in `README.md` that prompt edits require the Step26 quality test and that live E2E requires configured provider credentials.

- [ ] **Step 4: Run the quality and full suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: Step26 tests and all credential-independent tests pass. Any live credential-dependent failures must be reported with their exact missing-credential cause, not masked.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_step26_prompt_quality.py README.md
git commit -m "test: guard agent prompt quality across the workflow"
```
