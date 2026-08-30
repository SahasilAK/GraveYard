import json
import logging
import os
from typing import Any, Dict
from scrum_team.memory_store import get_memory, put_memory, search_memory

logger = logging.getLogger(__name__)


def extract_and_store_memories(state: Dict[str, Any], store: Any = None) -> None:
    """
    Fail-soft memory extraction step executed at completion points.
    Captures cross-project learnings for Developer, PO, QA, and Project summaries.
    """
    try:
        project_id = state.get("project_id", "default_project")
        status = state.get("status", "")
        brief_raw = state.get("brief", "")
        backlog = state.get("backlog", [])
        dev_output = state.get("dev_output", {})
        qa_smoke = state.get("qa_smoke_results", {})
        qa_full = state.get("qa_full_results", {})
        human_feedback = state.get("human_feedback") or state.get("raw_input")

        # 1. Project Summary -> ("projects", project_id, "summary")
        brief_text = ""
        if brief_raw:
            try:
                brief_json = json.loads(brief_raw) if isinstance(brief_raw, str) else brief_raw
                brief_text = brief_json.get("goal", str(brief_json))
            except Exception:
                brief_text = str(brief_raw)[:200]

        files_changed = dev_output.get("files_changed", []) if isinstance(dev_output, dict) else []

        proj_summary_value = {
            "project_id": project_id,
            "goal": brief_text,
            "total_tasks": len(backlog),
            "status": status,
            "artifacts": files_changed,
        }
        
        _safe_put(("projects", project_id, "summary"), "overview", proj_summary_value, store=store)

        # 2. Developer Code Pattern -> ("developer", "code_patterns")
        dev_key = f"pattern_{project_id}"
        dev_pattern_value = {
            "project_id": project_id,
            "pattern": f"Implementation module for {project_id}",
            "artifacts": files_changed,
            "summary": dev_output.get("summary", "") if isinstance(dev_output, dict) else "",
        }
        _safe_put(("developer", "code_patterns"), dev_key, dev_pattern_value, store=store)

        # Rework lesson if human feedback was captured
        if human_feedback:
            rework_key = f"rework_{project_id}"
            rework_value = {
                "project_id": project_id,
                "feedback": str(human_feedback),
                "lesson": f"Resolved rework request for {project_id}",
            }
            _safe_put(("developer", "code_patterns"), rework_key, rework_value, store=store)

        # 3. Product Owner DoD Preference -> ("po", "dod_preferences")
        po_key = "standard_dod"
        po_dod_value = {
            "acceptance_criteria_pattern": "Goal statement + acceptance criteria + prioritized backlog",
            "last_project": project_id,
        }
        _safe_put(("po", "dod_preferences"), po_key, po_dod_value, store=store)

        # 4. QA Test Pattern -> ("qa", "test_patterns")
        qa_key = "smoke_and_full_verification"
        qa_pattern_value = {
            "smoke_check": qa_smoke.get("details", "Basic smoke check passed") if isinstance(qa_smoke, dict) else "Smoke passed",
            "full_qa": qa_full.get("details", "Full QA verification passed") if isinstance(qa_full, dict) else "Full QA passed",
            "last_project": project_id,
        }
        _safe_put(("qa", "test_patterns"), qa_key, qa_pattern_value, store=store)

        logger.info(f"Successfully extracted and stored cross-project memories for '{project_id}'.")

    except Exception as e:
        logger.error(f"Fail-soft memory extraction failed: {e}", exc_info=True)


def _safe_put(namespace: tuple[str, ...], key: str, value: Dict[str, Any], store: Any = None) -> None:
    """Helper to update item in store if exists or write new item."""
    try:
        if store is not None and hasattr(store, "put"):
            existing = None
            if hasattr(store, "get"):
                existing = store.get(namespace, key)
            if existing and hasattr(existing, "value") and isinstance(existing.value, dict):
                # Update in place
                merged = dict(existing.value)
                merged.update(value)
                store.put(namespace, key, merged)
            else:
                store.put(namespace, key, value)
        else:
            existing = get_memory(namespace, key)
            if existing and hasattr(existing, "value") and isinstance(existing.value, dict):
                merged = dict(existing.value)
                merged.update(value)
                put_memory(namespace, key, merged)
            else:
                put_memory(namespace, key, value)
    except Exception as e:
        logger.warning(f"Failed writing memory for {namespace}/{key}: {e}")
