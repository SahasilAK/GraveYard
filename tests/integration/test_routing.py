import pytest
from scrum_team.graph import scrum_master_router
from scrum_team.state import ScrumTeamState

def test_routing_to_prompt_agent():
    state: ScrumTeamState = {"project_id": "p1", "raw_input": "New task", "backlog": []}
    assert scrum_master_router(state) == "prompt_agent"

def test_routing_to_po_agent():
    state: ScrumTeamState = {"project_id": "p1", "raw_input": None, "brief": "Goal", "backlog": []}
    assert scrum_master_router(state) == "po_agent"

def test_routing_to_dev_when_planning():
    state: ScrumTeamState = {"project_id": "p1", "raw_input": None, "brief": "Goal", "backlog": [{"id": "t1"}], "status": "planning"}
    assert scrum_master_router(state) == "dev_agent"

def test_routing_to_qa_smoke():
    state: ScrumTeamState = {"project_id": "p1", "raw_input": None, "brief": "Goal", "backlog": [{"id": "t1"}], "status": "qa_smoke"}
    assert scrum_master_router(state) == "qa_agent"

def test_routing_to_human_review():
    state: ScrumTeamState = {"project_id": "p1", "raw_input": None, "brief": "Goal", "backlog": [{"id": "t1"}], "status": "qa_approval"}
    assert scrum_master_router(state) == "human_review"

def test_routing_end():
    state: ScrumTeamState = {"project_id": "p1", "raw_input": None, "brief": "Goal", "backlog": [{"id": "t1", "status" : "done"}], "status": "finished"}
    assert scrum_master_router(state) == "__end__"
