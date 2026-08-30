from scrum_team.utils.llm_factory import get_llm
from scrum_team.utils.backlog_schema import BacklogSchema, TaskItemSchema
from scrum_team.memory_retriever import get_po_memory_context
from scrum_team.common.entities import Plan, Task, AtomicTask
from scrum_team.middleware.error_handler import execute_with_retry
from scrum_team.agents.prompt_loader import load_prompt
import logging
import json

logger = logging.getLogger(__name__)

def generate_backlog(brief: str) -> BacklogSchema:
    def _invoke():
        llm = get_llm("PO")
        structured_llm = llm.with_structured_output(BacklogSchema)
        memory_ctx = get_po_memory_context()
        prompt = f"{load_prompt('PO')}\n\nBrief:\n{brief[:1500]}"
        if memory_ctx:
            prompt += f"\n{memory_ctx}"
        return structured_llm.invoke(prompt)

    try:
        return execute_with_retry(_invoke, max_retries=2, task_name="PO Backlog Generation")
    except Exception as e:
        logger.error(f"PO Agent error: {e}. Falling back to default backlog item.")
        return BacklogSchema(
            items=[
                TaskItemSchema(
                    id="TASK-1",
                    title="Implement requested core functionality",
                    description="Core implementation based on brief summary.",
                    acceptance_criteria=["Code compiles and runs without error"]
                )
            ]
        )

def generate_plan_from_backlog(backlog_item: dict) -> Plan:
    """Converts a single backlog task dict into a structured Plan object."""
    def _invoke():
        llm = get_llm("PO")
        structured_llm = llm.with_structured_output(Plan)
        
        prompt = (
            f"{load_prompt('PO')}\n\n"
            "Decompose the following task into a structured Plan of 1-3 Tasks. "
            "Each Task targets ONE file area. Every AtomicTask must describe concrete behavior, its public signature, "
            "a function/class or exact code area, expected inputs and outputs/types, normal and "
            "edge-case behavior, required imports, and at least one concrete example or acceptance "
            "check. Put examples, constraints, and integration assumptions in additional_context. "
            "Do not return vague labels such as implement the feature, add support, or import a library.\n\n"
            f"Task Title: {backlog_item.get('title', 'Feature')}\n"
            f"Description: {backlog_item.get('description', '')}\n"
            f"Acceptance Criteria: {backlog_item.get('acceptance_criteria', [])}"
        )
        return structured_llm.invoke(prompt)

    try:
        return execute_with_retry(_invoke, max_retries=2, task_name="PO Plan Generation")
    except Exception as e:
        logger.error(f"PO Plan error: {e}. Returning fallback plan.")
        description = str(backlog_item.get("description", "")).strip()
        criteria = "; ".join(backlog_item.get("acceptance_criteria", []))
        task_id = backlog_item.get("id", "TASK-1")
        title = backlog_item.get("title", "Default implementation")
        return Plan(
            tasks=[
                Task(
                    file_path=f"{task_id}.py",
                    logical_task=title,
                    atomic_tasks=[
                        AtomicTask(
                            atomic_task=(
                                f"Implement the requested behavior for '{title}' in {task_id}. "
                                "Define a public entry point, accept the described inputs, return "
                                "the requested output, and handle invalid or empty input without "
                                f"placeholder logic. Description: {description}"
                            ),
                            additional_context=(
                                f"Acceptance criteria: {criteria}. If no signature is specified, "
                                "choose and document a small callable signature that directly "
                                "satisfies the description."
                            )
                        )
                    ]
                )
            ]
        )

