import os
import logging
from pathlib import Path
from typing import Dict, Any
from scrum_team.common.entities import DiffTask
from scrum_team.tools.permissions import validate_project_path, check_agent_tool_permission

logger = logging.getLogger(__name__)

def apply_diff_task(diff_task: DiffTask, project_path: str | Path, agent_role: str = "DEVELOPER") -> Dict[str, Any]:
    """
    Applies an atomic DiffTask to a file inside projects/<project_name>/.
    Enforces agent tool permission checks and path isolation scoping.
    """
    try:
        check_agent_tool_permission(agent_role, "apply_diff")
        target_path = validate_project_path(diff_task.file_path, project_path)
    except PermissionError as pe:
        logger.error(f"Permission failure in apply_diff_task: {pe}")
        return {"success": False, "error": str(pe), "file_path": diff_task.file_path}

    proj_root = Path(project_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    orig_snippet = diff_task.original_code_snippet
    new_snippet = diff_task.new_code_snippet

    # 1. New File or Insertion
    if not target_path.exists() or not orig_snippet.strip():
        try:
            if not target_path.exists():
                target_path.write_text(new_snippet, encoding="utf-8")
                action = "created_file"
            else:
                current_content = target_path.read_text(encoding="utf-8")
                updated_content = current_content + ("\n" if current_content and not current_content.endswith("\n") else "") + new_snippet
                target_path.write_text(updated_content, encoding="utf-8")
                action = "appended_code"

            return {
                "success": True,
                "action": action,
                "file_path": str(target_path.relative_to(proj_root)),
                "summary": f"Atomic {action} for '{diff_task.task_description[:50]}'"
            }
        except Exception as e:
            logger.error(f"Failed writing target file {target_path}: {e}")
            return {"success": False, "error": str(e), "file_path": diff_task.file_path}

    # 2. Targeted Replacement
    try:
        content = target_path.read_text(encoding="utf-8")

        # Try exact replacement
        if orig_snippet in content:
            updated_content = content.replace(orig_snippet, new_snippet, 1)
            target_path.write_text(updated_content, encoding="utf-8")
            return {
                "success": True,
                "action": "replaced_snippet",
                "file_path": str(target_path.relative_to(proj_root)),
                "summary": f"Applied atomic diff to '{diff_task.task_description[:50]}'"
            }

        # Try whitespace/line-strip normalized match
        orig_lines = [line.rstrip() for line in orig_snippet.strip().splitlines()]
        content_lines = content.splitlines()
        
        match_start_idx = -1
        for i in range(len(content_lines) - len(orig_lines) + 1):
            window = [line.rstrip() for line in content_lines[i : i + len(orig_lines)]]
            if window == orig_lines:
                match_start_idx = i
                break

        if match_start_idx != -1:
            new_lines = content_lines[:match_start_idx] + [new_snippet] + content_lines[match_start_idx + len(orig_lines):]
            updated_content = "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")
            target_path.write_text(updated_content, encoding="utf-8")
            return {
                "success": True,
                "action": "replaced_snippet_normalized",
                "file_path": str(target_path.relative_to(proj_root)),
                "summary": f"Applied normalized atomic diff to '{diff_task.task_description[:50]}'"
            }

        error_msg = f"Original code snippet not found in target file '{diff_task.file_path}'."
        logger.warning(error_msg)
        return {"success": False, "error": error_msg, "file_path": diff_task.file_path}

    except Exception as e:
        logger.error(f"Error applying diff to {target_path}: {e}")
        return {"success": False, "error": str(e), "file_path": diff_task.file_path}
