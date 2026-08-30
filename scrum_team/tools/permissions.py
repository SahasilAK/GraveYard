import os
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Strict Agent Tool Permission Registry
AGENT_TOOL_PERMISSIONS: Dict[str, List[str]] = {
    "PROMPT_AGENT": [],  # Pure text-in, structured-brief-out
    "PRODUCT_OWNER": ["get_project_backlog"],  # Read-only backlog state
    "SCRUM_MASTER": ["route_workflow"],  # Routing only, no file access
    "DEVELOPER": ["search_code", "apply_diff", "read_project_file", "write_project_file"],
    "QA_ENGINEER": ["search_code", "read_project_file", "run_smoke_test"],
    "REVIEWER": ["search_code", "read_project_file"]  # Read-only inspection, no write access
}

def validate_project_path(target_path: str | Path, project_path: str | Path) -> Path:
    """
    Enforces strict path isolation scoping at the tool level.
    Ensures target_path resolves inside projects/<project_name>/.
    Raises PermissionError if target path attempts path traversal.
    """
    proj_root = Path(project_path).resolve()
    target_abs = (proj_root / Path(target_path)).resolve()
    
    try:
        target_abs.relative_to(proj_root)
    except ValueError:
        error_msg = f"Security scoping violation: Path '{target_path}' (resolved: '{target_abs}') is outside project boundary '{proj_root}'"
        logger.error(error_msg)
        raise PermissionError(error_msg)

    return target_abs

def check_agent_tool_permission(agent_role: str, tool_name: str) -> None:
    """
    Validates that the specified agent_role is authorized to call tool_name.
    """
    allowed_tools = AGENT_TOOL_PERMISSIONS.get(agent_role, [])
    if tool_name not in allowed_tools:
        error_msg = f"Permission denied: Agent '{agent_role}' is not authorized to call tool '{tool_name}'"
        logger.error(error_msg)
        raise PermissionError(error_msg)

def read_project_file_scoped(file_path: str | Path, project_path: str | Path, agent_role: str) -> str:
    """
    Reads a file inside projects/<project_name>/ after verifying agent permission and path scoping.
    """
    check_agent_tool_permission(agent_role, "read_project_file")
    resolved_file = validate_project_path(file_path, project_path)
    
    if not resolved_file.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist inside project directory.")
        
    return resolved_file.read_text(encoding="utf-8")
