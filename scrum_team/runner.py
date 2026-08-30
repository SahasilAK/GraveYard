import os
import threading
from langgraph.types import Command
from scrum_team.graph import create_graph

# Global graph instance with persistent checkpoint DB
graph = create_graph("data/checkpoints.db")

# Stop signal for aborting a running pipeline
_stop_event = threading.Event()

def request_stop():
    """Call from the UI to abort the current graph run."""
    _stop_event.set()

def is_stop_requested() -> bool:
    return _stop_event.is_set()

def get_project_config(project_id: str) -> dict:
    return {"configurable": {"thread_id": project_id}}

def get_project_state(project_id: str):
    config = get_project_config(project_id)
    return graph.get_state(config)

def run_project_graph(project_id: str, raw_input: str = None, resume_command: dict = None, log_callback=None):
    """
    Executes or resumes a project graph run, calling log_callback(message) for real-time UI logging.
    """
    _stop_event.clear()
    config = get_project_config(project_id)
    
    if resume_command is not None:
        input_payload = Command(resume=resume_command)
        if log_callback:
            if resume_command.get("approved"):
                log_callback(f"[Human Review] Approved output for '{project_id}'. Resuming pipeline...")
            else:
                log_callback(f"[Human Review] Rejected output for '{project_id}'. Rework feedback: {resume_command.get('feedback')}")
    else:
        # Check if project has state already
        current_state = graph.get_state(config)
        if current_state and current_state.values:
            input_payload = {"raw_input": raw_input}
        else:
            input_payload = {"project_id": project_id, "raw_input": raw_input}
            
        if log_callback:
            log_callback(f"[Scrum Master] Starting graph run for project '{project_id}'...")

    # Stream execution steps
    for event in graph.stream(input_payload, config=config, stream_mode="updates"):
        if _stop_event.is_set():
            if log_callback:
                log_callback("🛑 [SYSTEM] Execution halted by user request.")
            break

        for node_name, updates in event.items():
            if node_name == "scrum_master":
                continue
            if not updates:
                continue
            
            if log_callback:
                if node_name == "prompt_agent":
                    log_callback(f"[Prompt Agent] Converted raw input into structured brief (retrieved past project summaries).")
                elif node_name == "po_agent":
                    backlog = updates.get("backlog", [])
                    log_callback(f"[Product Owner] Created/updated product backlog ({len(backlog)} user stories; applied DoD memory).")
                elif node_name == "dev_agent":
                    out = updates.get("dev_output", {})
                    task_id = updates.get("current_task_id", out.get("task_id", ""))
                    files = ", ".join(out.get("files_changed", []))
                    
                    # Log research steps
                    res_notes = out.get("research_notes", [])
                    for note in res_notes:
                        log_callback(f"[Developer Research] {note}")

                    log_callback(f"[Developer] Created code artifacts for task {task_id} (applied code pattern memory): {files}")
                elif node_name == "qa_agent":
                    results = updates.get("qa_smoke_results", {})
                    passed = results.get("passed", False)
                    log_callback(f"[QA Engineer] Smoke test {'PASSED' if passed else 'FAILED'} (applied QA pattern memory): {results.get('details', '')}")
                elif node_name == "human_review":
                    log_callback(f"[Human Review] Paused at approval checkpoint.")
                elif node_name == "reviewer":
                    next_st = updates.get("status", "")
                    if next_st == "planning":
                        log_callback("[Reviewer Agent] Task approved! Advancing to next task in backlog...")
                    else:
                        log_callback("[Reviewer Agent] Completed full code review & final QA checks for all backlog items!")

    # Return updated state
    return graph.get_state(config)
