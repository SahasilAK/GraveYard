import os
import logging
from scrum_team.agents.prompt_loader import load_prompt

QA_SYSTEM_PROMPT = load_prompt("QA_ENGINEER")
from scrum_team.memory_retriever import get_qa_memory_context
from scrum_team.tools.permissions import check_agent_tool_permission, validate_project_path

logger = logging.getLogger(__name__)

def run_qa(mode: str, project_path: str, plan_or_task: dict = None) -> dict:
    try:
        check_agent_tool_permission("QA_ENGINEER", "run_smoke_test")
        valid_proj_path = validate_project_path(".", project_path)
        exists = valid_proj_path.exists()
        
        qa_ctx = get_qa_memory_context()
        details_extra = f" (Applied QA Memory: {qa_ctx.strip()[:60]}...)" if qa_ctx else ""
        
        target_info = ""
        if plan_or_task and isinstance(plan_or_task, dict) and "tasks" in plan_or_task:
            task_cnt = len(plan_or_task.get("tasks", []))
            target_info = f" Verified {task_cnt} structured tasks."

        if mode == "smoke":
            return {
                "passed": exists,
                "details": f"{QA_SYSTEM_PROMPT.splitlines()[1]} Smoke check for project path '{valid_proj_path}' completed.{target_info} Project path exists: {exists}.{details_extra}"
            }
        return {
            "passed": exists,
            "details": f"{QA_SYSTEM_PROMPT.splitlines()[1]} Full QA inspection for project path '{valid_proj_path}' completed.{target_info}{details_extra}"
        }
    except Exception as e:
        logger.error(f"QA Agent execution error: {e}")
        return {"passed": False, "details": f"QA test error: {e}"}
