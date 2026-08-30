import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from scrum_team.tools.permissions import check_agent_tool_permission, validate_project_path

logger = logging.getLogger(__name__)

def search_project_codebase(project_path: str | Path, query: str, max_results: int = 10, agent_role: str = "DEVELOPER") -> List[Dict[str, Any]]:
    """
    Searches text/regex within files in projects/<project_name>/.
    Strictly scoped to project_path to prevent accessing outside directories.
    Enforces permission check for agent_role.
    """
    check_agent_tool_permission(agent_role, "search_code")
    path = validate_project_path(".", project_path)
    results = []
    
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return results

    if not path.is_dir():
        logger.warning(f"Search path is not a directory: {path}")
        return results

    try:
        regex = re.compile(query, re.IGNORECASE)
    except Exception:
        # Fall back to literal string match if query is not valid regex
        regex = re.compile(re.escape(query), re.IGNORECASE)

    try:
        for root, _, files in os.walk(path):
            for file in files:
                if len(results) >= max_results:
                    break
                
                filepath = Path(root) / file
                # Scoping check
                try:
                    rel_path = filepath.relative_to(path)
                except ValueError:
                    continue

                if file.startswith(".") or file.endswith(".pyc"):
                    continue

                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    for line_num, line in enumerate(lines, start=1):
                        if regex.search(line):
                            results.append({
                                "file": str(rel_path),
                                "line_num": line_num,
                                "content": line.strip()[:150]
                            })
                            if len(results) >= max_results:
                                break
                except Exception as e:
                    logger.debug(f"Could not read {filepath}: {e}")
    except Exception as e:
        logger.error(f"Project codebase search error: {e}")

    return results
