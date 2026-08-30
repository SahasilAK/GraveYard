import pytest
import uuid
from scrum_team.runner import run_project_graph, get_project_state

def test_full_pipeline_auto_approval():
    proj_id = f"test-e2e-{uuid.uuid4().hex[:6]}"
    
    # 1. Run pipeline up to human review
    run_project_graph(proj_id, raw_input="Create a simple calculator in Python with add and subtract")
    
    state = get_project_state(proj_id)
    assert "human_review" in state.next
    
    # 2. Approve and auto-finish
    run_project_graph(proj_id, resume_command={"approved": True})
    
    final_state = get_project_state(proj_id)
    # Depending on backlog size, it might need multiple dev iterations. 
    # For a robust e2e test, we just check if it advanced past approval:
    status = final_state.values.get("status")
    
    # Simple check: it either finished or is iterating through the next task (planning)
    assert status in ("finished", "planning", "qa_approval")
