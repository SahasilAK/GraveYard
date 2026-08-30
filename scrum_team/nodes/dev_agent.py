import ast
import logging
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from scrum_team.common.entities import DiffTask, GeneratedCode
from scrum_team.memory_retriever import get_dev_memory_context
from scrum_team.utils.code_search import search_project_codebase
from scrum_team.utils.diff_applier import apply_diff_task
from scrum_team.utils.llm_factory import get_llm

logger = logging.getLogger(__name__)
MAX_RESEARCH_STEPS = 2
MAX_GENERATION_ATTEMPTS = 3

from scrum_team.agents.prompt_loader import load_prompt

DEVELOPER_SYSTEM_PROMPT = load_prompt("DEVELOPER")
QA_SYSTEM_PROMPT = load_prompt("QA_ENGINEER")
REVIEWER_SYSTEM_PROMPT = load_prompt("REVIEWER")
PROMPT_AGENT_SYSTEM_PROMPT = load_prompt("PROMPT_AGENT")
PO_SYSTEM_PROMPT = load_prompt("PO")
SCRUM_MASTER_SYSTEM_PROMPT = load_prompt("SCRUM_MASTER")

# Kept as named constants for compatibility and prompt auditing.

_PLACEHOLDER_MARKERS = (
    "atomic step",
    "feature implemented successfully",
    "todo",
    "fixme",
    "pseudo",
    "pseudocode",
    "placeholder",
    "not implemented",
    "notimplementederror",
    "mock",
)


class _GenerationValidationError(ValueError):
    """Raised when every generated candidate fails the validation gate."""

    def __init__(self, message: str, validation_events: list[str]):
        super().__init__(message)
        self.validation_events = validation_events


def _expected_operation(task_description: str, file_path: str) -> tuple[str, tuple[str, ...]] | None:
    """Return a required library/operation only for unambiguous task wording."""
    context = f"{task_description} {file_path}".lower()
    if "csv" in context:
        return "CSV parsing", ("csv", "dictreader", "reader", "read_csv")
    if "json" in context:
        return "JSON handling", ("json", "loads", "dumps", "load", "dump")
    if "yaml" in context:
        return "YAML handling", ("yaml", "safe_load", "safe_dump", "load", "dump")
    if "xml" in context:
        return "XML handling", ("xml", "elementtree", "parse", "fromstring")
    if "database" in context or " db " in f" {context} " or " sql " in f" {context} ":
        return "database access", ("sqlite", "sqlalchemy", "psycopg", "mysql", "connect", "execute", "cursor")
    if "api endpoint" in context or "rest api" in context or "http endpoint" in context:
        return "API endpoint", ("route", "get", "post", "put", "patch", "delete", "fastapi", "flask", "http")
    return None


def _matches_operation(value: str, markers: tuple[str, ...]) -> bool:
    normalized = value.lower()
    return any(
        normalized == marker
        or normalized.endswith(f".{marker}")
        for marker in markers
    )


def _references_operation(tree: ast.AST, markers: tuple[str, ...]) -> bool:
    """Check executable calls/attributes, not imports, function names, or comments."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and _matches_operation(node.attr, markers):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if _matches_operation(node.func.id, markers):
                return True
    return False


def _returns_default_literal(node: ast.Return) -> bool:
    value = node.value
    return isinstance(value, ast.Constant) and value.value in (None, "", 0, False)


def _has_real_control_flow(body: list[ast.stmt]) -> bool:
    return any(isinstance(item, (ast.Return, ast.With, ast.For, ast.If, ast.Try, ast.Assign)) for item in body)


def validate_generated_code(code: str, file_path: str, task_description: str = "") -> tuple[bool, str]:
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

    requirement = _expected_operation(task_description, file_path)
    if requirement:
        label, markers = requirement
        if not _references_operation(tree, markers):
            return False, f"Task requires {label}, but the implementation does not reference the expected library or operation."

    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            return False, "Generated code contains a placeholder pass statement."
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = [item for item in node.body if not isinstance(item, ast.Expr) or not isinstance(getattr(item, "value", None), ast.Constant) or not isinstance(item.value.value, str)]
            if body and all(isinstance(item, ast.Expr) and isinstance(item.value, ast.Call) and isinstance(getattr(item.value.func, "id", None), str) and item.value.func.id in {"print", "logging", "log"} for item in body):
                return False, f"Function {node.name} only prints/logs and contains no implementation."
            if len(body) <= 1 and any(word in task_description.lower() for word in ("parse", "connect", "save", "load", "calculate", "process")) and not any(isinstance(item, (ast.Return, ast.With, ast.For, ast.If, ast.Try, ast.Assign)) for item in body):
                return False, f"Function {node.name} is suspiciously short for the requested task."
    return True, ""




def conduct_task_research(task: dict, project_path: str, max_steps: int = MAX_RESEARCH_STEPS) -> list:
    research_logs = []
    logical_task = task.get("logical_task", "")
    target_file = task.get("file_path", "")
    keywords = [w for w in logical_task.replace("/", " ").replace("_", " ").split() if len(w) > 3]
    if target_file:
        base_name = os.path.splitext(os.path.basename(target_file))[0]
        if base_name and base_name not in keywords:
            keywords.insert(0, base_name)

    for steps_taken, keyword in enumerate(keywords[:max_steps], start=1):
        matches = search_project_codebase(project_path, keyword, max_results=5)
        if matches:
            research_logs.append(f"[Research Step {steps_taken}] Searched '{keyword}': found {len(matches)} matches in existing codebase.")
        else:
            research_logs.append(f"[Research Step {steps_taken}] Searched '{keyword}': no prior code found (new area).")
    if len(keywords) > max_steps:
        research_logs.append(f"[Research Cap] Reached max research steps ({max_steps}). Proceeding with implementation.")
    return research_logs or ["[Research Step 1] Initialized workspace scan: targeting new code creation."]


def _generation_prompt(task: dict, current_code: str, feedback: str = "") -> str:
    atomic_details = "\n".join(
        f"- {item.get('atomic_task', item) if isinstance(item, dict) else item}\n"
        f"  Context: {item.get('additional_context', '') if isinstance(item, dict) else ''}"
        for item in task.get("atomic_tasks", [])
    )
    return (
        f"Target file: {task.get('file_path', 'app.py')}\n"
        f"Overall task: {task.get('logical_task', '')}\n"
        f"Implementation requirements:\n{atomic_details}\n\n"
        f"Existing file contents (replace with a complete file; empty means create it):\n"
        f"```python\n{current_code}\n```\n{feedback}"
    )


def generate_file_code(task: dict, current_code: str, llm=None, max_attempts: int = MAX_GENERATION_ATTEMPTS) -> GeneratedCode:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    structured_llm = (llm or get_llm("DEVELOPER")).with_structured_output(GeneratedCode)
    feedback = ""
    validation_events = []
    file_path = task.get("file_path", "app.py")
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        response = structured_llm.invoke([
            SystemMessage(content=DEVELOPER_SYSTEM_PROMPT),
            HumanMessage(content=_generation_prompt(task, current_code, feedback)),
        ])
        result = response if isinstance(response, GeneratedCode) else GeneratedCode.model_validate(response)
        if result.status == "blocked":
            raise ValueError(f"Developer marked task blocked: {result.notes or 'missing requirements'}")
        valid, last_error = validate_generated_code(result.code, file_path, task.get("logical_task", ""))
        if valid:
            result.validation_events = validation_events + [
                f"[Validation Gate] accepted {file_path} on attempt {attempt}/{max_attempts}."
            ]
            return result
        event = f"[Validation Gate] rejected {file_path} on attempt {attempt}/{max_attempts}: {last_error}"
        validation_events.append(event)
        logger.warning(event)
        feedback = f"\nVALIDATION FEEDBACK: {last_error} Correct the source and return the entire complete file; do not return a stub.\n"
    raise _GenerationValidationError(
        f"Generated code failed validation after {max_attempts} attempts: {last_error}",
        validation_events,
    )


def _validation_events_from_error(exc: Exception) -> list[str]:
    return list(getattr(exc, "validation_events", []))


def _log_validation_events(events: list[str], log_callback=None) -> None:
    for event in events:
        logger.info(event)
        if log_callback:
            log_callback(event)


def _task_file_path(task: dict) -> str:
    fpath = task.get("file_path", "app.py")
    return fpath if fpath.endswith(".py") else f"{fpath}.py"


def write_code(plan_or_task, project_path: str, llm=None, max_generation_attempts: int = MAX_GENERATION_ATTEMPTS, log_callback=None) -> dict:
    try:
        files_created, diff_results, all_research_notes, validation_events = [], [], [], []
        if isinstance(plan_or_task, dict) and "tasks" in plan_or_task:
            tasks = plan_or_task.get("tasks", [])
        else:
            title = plan_or_task.get("title", "Task") if isinstance(plan_or_task, dict) else str(plan_or_task)
            task_id = plan_or_task.get("id", "TASK-1") if isinstance(plan_or_task, dict) else "TASK-1"
            tasks = [{"file_path": f"{task_id}.py", "logical_task": title, "atomic_tasks": [{"atomic_task": title}]}]

        task_id = "TASK-1"
        for task in tasks:
            fpath = _task_file_path(task)
            task_id = fpath.removesuffix(".py").replace("/", "_")
            all_research_notes.extend(conduct_task_research(task, project_path))
            target = Path(project_path) / fpath
            current_code = target.read_text(encoding="utf-8") if target.exists() else ""
            try:
                generated = generate_file_code(task, current_code, llm=llm, max_attempts=max_generation_attempts)
                validation_events.extend(generated.validation_events)
                _log_validation_events(generated.validation_events, log_callback)
                result = apply_diff_task(DiffTask(
                    file_path=fpath,
                    original_code_snippet=current_code,
                    task_description=task.get("logical_task", "Implement task"),
                    new_code_snippet=generated.code,
                ), project_path)
            except Exception as exc:
                failed_events = _validation_events_from_error(exc)
                validation_events.extend(failed_events)
                _log_validation_events(failed_events, log_callback)
                logger.error("Developer generation failed for %s: %s", fpath, exc)
                result = {"success": False, "error": str(exc), "file_path": fpath}
            diff_results.append(result)
            if result.get("success"):
                files_created.append(result.get("file_path", fpath))

        return {"files_changed": files_created, "summary": f"Executed Plan across {len(files_created)} files.", "task_id": task_id, "diff_results": diff_results, "research_notes": all_research_notes, "validation_events": validation_events}
    except Exception as exc:
        logger.error("Dev Agent write error: %s", exc)
        return {"files_changed": [], "summary": f"Failed executing plan: {exc}", "error": str(exc), "diff_results": [], "research_notes": []}
