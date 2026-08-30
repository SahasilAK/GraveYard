# AI Scrum Team

Locally-hosted, autonomous multi-agent software development scrum team.

## Documentation

- [User Guide](docs/USER_GUIDE.md) — operating the dashboard and workflow.
- [Examples](docs/EXAMPLES.md) — sample briefs, expected flow, and regression commands.
- [Testing](docs/TESTING.md) — unit, prompt-regression, and full-suite commands.
- [Architecture](docs/ARCHITECTURE.md) — agent roles, state, storage, and validation gate.
- [Production Readiness](docs/PRODUCTION_READINESS.md) — release, operations, and safety checklist.

## Setup
1. Clone the repository.
2. Run `first_run.bat` to create the environment and install dependencies.
3. Run `start_app.bat` to launch the web dashboard.

## Usage
- **New Project**: Use the Chat tab to start a new project; the team breaks down the brief and begins execution.
- **Human-in-the-Loop**: The run pauses for dev output review. Use the UI to "Approve" or "Request Rework".
- **Logs**: Monitor active agents and state transitions in the Logs tab.
- **Config**: Update model mappings in the OmniRoute settings.

## Storage
- **Projects**: Project outputs and source code are generated locally inside `projects/<project_name>/`.
- **Short-Term Checkpoint DB**: Thread execution state is persisted per-project to `data/checkpoints.db`. This allows the LangGraph to pause for human-in-the-loop review and successfully resume across UI restarts.
- **Long-Term Memory BaseStore**: Cross-project and cross-thread agent memories (e.g. Developer code conventions, PO definition-of-done preferences, and QA rules) are stored separately into `data/memory.db`.

### Resetting Memory
If the team generates "pattern learnings" that are overly rigid or incorrect, you can wipe them using the **Memory Manager** tab in the Streamlit UI. This allows you to inspect specific memories by namespace (e.g. `("developer", "code_patterns")`), selectively delete bad entries, or perform a total memory wipe of an entire namespace natively through the frontend.

## Automated Testing
To ensure system reliability, a suite of automated tests is included. To run them, use the developer-only script:
```bash
run_tests.bat
```
This suite covers:
- **Unit Tests**: Core agent logic (Prompt Agent structured output, DiffTask generation).
- **Integration Tests**: Graph routing, state conditions, and human-in-the-loop pauses.
- **E2E Tests**: Full pipeline regression using a fixture project.

## Prompt Regression Checks

Prompt templates are canonical files under `scrum_team/agents/prompts/`. After changing any prompt template, run the offline prompt regression suite before trusting the change against real projects:

```bash
python -m pytest tests/unit/test_prompt_templates.py tests/unit/test_step25_validation_gate.py tests/unit/test_step27_prompt_regression.py -q
```

This suite checks that Developer output still passes the Step 25 validation gate, placeholder code is rejected, PO acceptance criteria stay specific, QA output references the real work, and Reviewer output names inspected files. Live end-to-end runs require configured provider credentials and are separate from this offline gate.

## Agent Tool Permissions & Scoping Boundaries

| Agent Role | Allowed Tools | Permissions & Access Scope |
| --- | --- | --- |
| **Prompt Agent** | None | Pure text input to structured JSON brief. No file access. |
| **Product Owner** | `get_project_backlog` | Read-only access to project backlog and DoD preferences. |
| **Scrum Master** | `route_workflow` | State transition & graph routing only. No file system access. |
| **Developer** | `search_code`, `apply_diff`, `read_project_file`, `write_project_file` | Code search, atomic diff application, and file read/write strictly scoped inside `projects/<project_name>/`. |
| **QA Engineer** | `search_code`, `read_project_file`, `run_smoke_test` | Read-only file inspection & test execution inside `projects/<project_name>/`. No file write access. |
| **Reviewer** | `search_code`, `read_project_file` | Read-only code inspection inside `projects/<project_name>/`. No write access. |
