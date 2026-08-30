import logging
from typing import List, Optional
from scrum_team.memory_store import search_memory, get_memory

logger = logging.getLogger(__name__)


def get_prompt_agent_memory_context(limit: int = 3) -> str:
    """Retrieve top recent project summaries for Prompt Agent context."""
    try:
        results = search_memory(("projects",), limit=limit)
        if not results:
            return ""

        summaries = []
        for item in results:
            val = getattr(item, "value", {})
            if isinstance(val, dict):
                pid = val.get("project_id", "project")
                goal = val.get("goal", "")
                if goal:
                    summaries.append(f"- Project '{pid}': {goal[:100]}")

        if not summaries:
            return ""

        return "\n[Related Past Projects]\n" + "\n".join(summaries)
    except Exception as e:
        logger.warning(f"Failed retrieving Prompt Agent memory: {e}")
        return ""


def get_po_memory_context(limit: int = 2) -> str:
    """Retrieve top Definition of Done / backlog conventions for Product Owner."""
    try:
        results = search_memory(("po", "dod_preferences"), limit=limit)
        if not results:
            return ""

        dods = []
        for item in results:
            val = getattr(item, "value", {})
            if isinstance(val, dict):
                pat = val.get("acceptance_criteria_pattern")
                if pat:
                    dods.append(f"- DoD Pattern: {pat}")

        if not dods:
            return ""

        return "\n[Learned Backlog & DoD Conventions]\n" + "\n".join(dods)
    except Exception as e:
        logger.warning(f"Failed retrieving PO memory: {e}")
        return ""


def get_dev_memory_context(limit: int = 3) -> str:
    """Retrieve top learned code patterns and rework fixes for Developer."""
    try:
        results = search_memory(("developer", "code_patterns"), limit=limit)
        if not results:
            return ""

        patterns = []
        for item in results:
            val = getattr(item, "value", {})
            if isinstance(val, dict):
                if "lesson" in val:
                    patterns.append(f"- Rework Lesson ({val.get('project_id', '')}): {val.get('lesson', '')[:120]}")
                elif "pattern" in val:
                    patterns.append(f"- Pattern ({val.get('project_id', '')}): {val.get('pattern', '')[:120]}")

        if not patterns:
            return ""

        return "\n[Learned Code Patterns & Rework Lessons]\n" + "\n".join(patterns)
    except Exception as e:
        logger.warning(f"Failed retrieving Developer memory: {e}")
        return ""


def get_qa_memory_context(limit: int = 2) -> str:
    """Retrieve top test patterns for QA Engineer."""
    try:
        results = search_memory(("qa", "test_patterns"), limit=limit)
        if not results:
            return ""

        qa_pats = []
        for item in results:
            val = getattr(item, "value", {})
            if isinstance(val, dict):
                smoke = val.get("smoke_check")
                full = val.get("full_qa")
                if smoke or full:
                    qa_pats.append(f"- Smoke: {smoke[:80]} | Full QA: {full[:80]}")

        if not qa_pats:
            return ""

        return "\n[QA Verification Patterns]\n" + "\n".join(qa_pats)
    except Exception as e:
        logger.warning(f"Failed retrieving QA memory: {e}")
        return ""
