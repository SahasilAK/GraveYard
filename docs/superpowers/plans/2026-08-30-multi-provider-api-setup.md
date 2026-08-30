# Multi-Provider API Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users configure named OpenAI, Anthropic, Google, OmniRoute, and local OpenAI-compatible connections in the web app, then assign a model and connection independently for each agent role without storing credentials in tracked files.

**Architecture:** Replace the single OmniRoute config with a local YAML connection registry and role-to-model assignments. A provider-aware factory normalizes provider settings into LangChain chat model instances; the Streamlit page edits and validates the registry and assignments, persisting only to ignored `config/config.yaml`.

**Tech Stack:** Python, PyYAML, Streamlit, LangChain integrations already installed where available, pytest.

**Spec:** Approved architecture in conversation (2026-08-30); Codex excluded.

## Global Constraints

- Never commit or print API keys; redact secrets in diagnostics and tests.
- `config/config.yaml` remains local runtime state and is ignored by Git.
- `config/config.example.yaml` contains placeholders only.
- Preserve existing `get_llm(role)` callers and role names.
- Support provider types `openai`, `anthropic`, `google`, `omniroute`, and `local`.
- Validate every role assignment references an existing connection before saving.
- Keep the implementation focused; do not add provider SDK dependencies unless already installed.

---

### Task 1: Define connection and model configuration schema

**Files:**
- Modify: `config/settings.py`
- Modify: `config/config.example.yaml`
- Test: `tests/unit/test_settings.py`

**Interfaces:**
- Produce `DEFAULT_CONFIG` with `connections` and `model_mapping` entries shaped as `{connection: str, model: str}`.
- Produce `load_config()` that safely returns the schema when the local file is absent or invalid.
- Preserve legacy `omniroute` config migration compatibility while reading existing local files.

- [ ] Write tests covering defaults, valid YAML, and conversion of legacy `omniroute` plus string role mappings.
- [ ] Run `pytest tests/unit/test_settings.py -v`; confirm new tests fail before implementation.
- [ ] Implement schema normalization and a single config path helper; never log secret values.
- [ ] Update the example file with named connection placeholders and role assignments.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Implement provider-aware model factory

**Files:**
- Modify: `scrum_team/utils/llm_factory.py`
- Test: `tests/unit/test_llm_factory.py`

**Interfaces:**
- Keep `get_llm(role: str) -> BaseChatModel` as the public entry point.
- Add `build_llm(connection: dict, model: str)` as the provider dispatch seam.
- Use `ChatOpenAI` for `openai`, `omniroute`, and `local`; use installed provider integrations for Anthropic/Google when available, otherwise raise a clear configuration error.

- [ ] Add tests mocking constructors and asserting provider, model, API key, and base URL are selected correctly; assert secret values never enter logs.
- [ ] Run focused factory tests and confirm failure.
- [ ] Implement provider dispatch with explicit required-field validation and no fallback to a real credential.
- [ ] Run focused factory tests and confirm pass.
- [ ] Run existing agent unit tests to catch caller regressions.

### Task 3: Replace the Streamlit configuration page

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/unit/test_app_config.py`

**Interfaces:**
- Rename navigation label to `API Setup`.
- Render `render_config()` with two sections: Connections and Model Selection.
- Support add/edit/remove named connections and role model/connection assignments.
- Save through the existing button flow to `config/config.yaml`, with validation before writing.

- [ ] Extract small pure helpers for draft normalization and save validation so they can be tested without launching Streamlit.
- [ ] Add tests for missing connection references, blank model names, and successful secret-preserving YAML serialization without asserting raw secret output.
- [ ] Run focused tests and confirm failure.
- [ ] Implement the UI using session state drafts, password inputs, masked existing keys, and safe provider-specific base URL fields.
- [ ] Ensure logs and success/error messages never contain API keys.
- [ ] Run focused tests and existing UI/backend integration tests.

### Task 4: Remove tracked secret and harden repository publishing

**Files:**
- Modify: `config/config.yaml` (local only; ensure no credential remains)
- Modify: `.gitignore`
- Modify: `config/config.example.yaml`

- [ ] Replace any current local API key with an empty value without displaying it.
- [ ] Ensure `.gitignore` excludes `config/config.yaml`, `.env`, and Streamlit secrets while allowing the example file.
- [ ] Search project files excluding `.venv`, caches, and generated files for common key formats and credential assignments.
- [ ] Verify the example has no non-placeholder secret and the runtime file is ignored.

### Task 5: Full verification

**Files:**
- No production files unless fixes are required.

- [ ] Run the complete test suite with `.venv/Scripts/python.exe -m pytest`.
- [ ] Run a syntax/import check for changed Python modules.
- [ ] Report any unavailable optional provider integration explicitly rather than silently pretending it works.
- [ ] Confirm configuration entered in the UI is usable after app restart and is absent from Git candidate files.
