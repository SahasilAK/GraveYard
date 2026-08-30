import sqlite3
import os
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from scrum_team.state import ScrumTeamState
from scrum_team.nodes.prompt_agent import generate_brief
from scrum_team.nodes.po_agent import generate_backlog
from scrum_team.nodes.dev_agent import write_code
from scrum_team.nodes.qa_agent import run_qa
from scrum_team.nodes.reviewer_agent import review_code
from scrum_team.memory_extractor import extract_and_store_memories
from scrum_team.agents.prompt_loader import load_prompt

SCRUM_MASTER_SYSTEM_PROMPT = load_prompt("SCRUM_MASTER")

# ── Nodes ──────────────────────────────────────────────────────────────

from scrum_team.nodes.po_agent import generate_backlog, generate_plan_from_backlog

def prompt_agent_node(state: ScrumTeamState):
    print("[ACTIVE] Prompt Agent...")
    if not state.get("raw_input"): return state
    brief = generate_brief(state["raw_input"])
    return {"brief": brief.model_dump_json(), "status": "planning", "raw_input": None}

def po_agent_node(state: ScrumTeamState):
    print("[ACTIVE] PO Agent...")
    backlog_obj = generate_backlog(state.get("brief", ""))
    backlog_items = [item.model_dump() for item in backlog_obj.items] if hasattr(backlog_obj, 'items') else []
    
    task_map = {}
    for item in backlog_items:
        tid = item.get("id", "TASK-1")
        task_map[tid] = "todo"
        
    return {
        "backlog": backlog_items,
        "task_status_map": task_map,
        "completed_task_ids": [],
        "in_progress_task_id": None,
        "status": "planning"
    }

def dev_agent_node(state: ScrumTeamState):
    print("[ACTIVE] Dev Agent...")
    backlog = state.get("backlog", [])
    completed_ids = state.get("completed_task_ids") or []
    task_map = dict(state.get("task_status_map") or {})
    
    # Find next incomplete task
    task_to_do = None
    for item in backlog:
        if isinstance(item, dict):
            tid = item.get("id", "")
            if tid not in completed_ids and item.get("status") != "done":
                task_to_do = item
                break
            
    if not task_to_do:
        task_to_do = backlog[0] if backlog else {"id": "TASK-1", "title": "Initial Implementation"}
        
    task_id = task_to_do.get("id") if isinstance(task_to_do, dict) else "TASK-1"
    task_map[task_id] = "in_progress"
    
    # Generate/Retrieve structured Plan object
    plan_obj = generate_plan_from_backlog(task_to_do)
    plan_dict = plan_obj.model_dump()
    
    project_id = state.get("project_id") or "default"
    out = write_code(plan_dict, os.path.join("projects", project_id))
    validation_events = out.get("validation_events", []) if isinstance(out, dict) else []
    failed = any(not item.get("success", False) for item in out.get("diff_results", [])) if isinstance(out, dict) else True
    return {
        "dev_output": out,
        "current_task_id": task_id,
        "in_progress_task_id": task_id,
        "task_status_map": task_map,
        "current_plan": plan_dict,
        "status": "failed" if failed else "qa_smoke",
        "validation_events": validation_events,
    }

def qa_agent_node(state: ScrumTeamState):
    print("[ACTIVE] QA Agent (Smoke Check)...")
    project_id = state.get("project_id") or "default"
    current_plan = state.get("current_plan")
    res = run_qa("smoke", os.path.join("projects", project_id), plan_or_task=current_plan)
    return {"qa_smoke_results": res, "status": "qa_approval"}

def human_review_node(state: ScrumTeamState):
    print("[WAITING] Human review interrupt...")
    feedback = interrupt({"prompt": "Approve or provide feedback on developer output:"})
    if feedback.get("approved"):
        return {"status": "full_qa"}
    
    user_fb = feedback.get("feedback")
    if user_fb:
        # Extract rework memory immediately on rejection
        try:
            project_id = state.get("project_id", "default")
            rework_key = f"rework_{project_id}"
            rework_val = {
                "project_id": project_id,
                "feedback": str(user_fb),
                "lesson": f"Human requested rework: {str(user_fb)[:150]}"
            }
            from scrum_team.memory_extractor import _safe_put
            _safe_put(("developer", "code_patterns"), rework_key, rework_val)
        except Exception as e:
            print(f"Failed to record rework memory: {e}")
            
    return {"raw_input": user_fb, "human_feedback": user_fb, "status": "planning"}

def reviewer_agent_node(state: ScrumTeamState):
    print("[ACTIVE] Reviewer Agent (Full QA & Review)...")
    project_id = state.get("project_id") or "default"
    out = review_code(os.path.join("projects", project_id))
    res = run_qa("full", os.path.join("projects", project_id))
    
    # Update current task status to 'done' in backlog
    curr_id = state.get("current_task_id")
    backlog = state.get("backlog", [])
    updated_backlog = []
    all_done = True
    
    for item in backlog:
        if isinstance(item, dict):
            item_copy = dict(item)
            if item_copy.get("id") == curr_id or not curr_id:
                item_copy["status"] = "done"
            if item_copy.get("status") != "done":
                all_done = False
            updated_backlog.append(item_copy)
        else:
            updated_backlog.append(item)
            
    # Update progress tracking state
    completed_ids = list(state.get("completed_task_ids") or [])
    if curr_id and curr_id not in completed_ids:
        completed_ids.append(curr_id)
        
    task_map = dict(state.get("task_status_map") or {})
    for tid in task_map:
        if tid in completed_ids:
            task_map[tid] = "done"
            
    next_status = "finished" if all_done else "planning"
    result = {
        "qa_full_results": res, 
        "backlog": updated_backlog,
        "completed_task_ids": completed_ids,
        "in_progress_task_id": None,
        "task_status_map": task_map,
        "status": next_status
    }
    
    # Fail-soft memory extraction pass at task / sprint completion point
    full_state = dict(state)
    full_state.update(result)
    extract_and_store_memories(full_state)

    return result

def scrum_master_node(state: ScrumTeamState): return {}

def scrum_master_router(state: ScrumTeamState) -> str:
    status = state.get("status", "")
    if state.get("raw_input"): return "prompt_agent"
    if not state.get("brief"): return "prompt_agent"
    if not state.get("backlog"): return "po_agent"
    if status == "planning": return "dev_agent"
    if status == "qa_smoke": return "qa_agent"
    if status == "qa_approval": return "human_review"
    if status == "full_qa": return "reviewer"
    return END

from scrum_team.memory_store import create_store
from scrum_team.middleware.error_handler import safe_node_execution

def create_graph(db_path: str = "data/checkpoints.db"):
    workflow = StateGraph(ScrumTeamState)
    
    # Wrap node executions in safe middleware wrapper to prevent unhandled node crashes
    def safe_prompt(state): return safe_node_execution("prompt_agent", prompt_agent_node, state)
    def safe_po(state): return safe_node_execution("po_agent", po_agent_node, state)
    def safe_dev(state): return safe_node_execution("dev_agent", dev_agent_node, state)
    def safe_qa(state): return safe_node_execution("qa_agent", qa_agent_node, state)
    def safe_review(state): return safe_node_execution("reviewer", reviewer_agent_node, state)

    nodes = {
        "scrum_master": scrum_master_node,
        "prompt_agent": safe_prompt,
        "po_agent": safe_po,
        "dev_agent": safe_dev,
        "qa_agent": safe_qa,
        "human_review": human_review_node,
        "reviewer": safe_review
    }
    for name, node in nodes.items(): workflow.add_node(name, node)
    workflow.set_entry_point("scrum_master")
    workflow.add_conditional_edges("scrum_master", scrum_master_router, {
        "prompt_agent": "prompt_agent", "po_agent": "po_agent",
        "dev_agent": "dev_agent", "qa_agent": "qa_agent",
        "human_review": "human_review", "reviewer": "reviewer", END: END
    })
    for node in ["prompt_agent", "po_agent", "dev_agent", "qa_agent", "human_review", "reviewer"]:
        workflow.add_edge(node, "scrum_master")
    checkpointer = SqliteSaver(sqlite3.connect(db_path, check_same_thread=False))
    store = create_store()
    return workflow.compile(checkpointer=checkpointer, store=store)
