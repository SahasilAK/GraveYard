import uuid
from scrum_team.common.entities import Plan, Task, AtomicTask
from scrum_team.runner import run_project_graph, get_project_state

def test_step16_structured_contracts():
    proj_id = f"test-step16-{uuid.uuid4().hex[:6]}"
    print(f"--- TESTING STEP 16 DATA CONTRACTS ON PROJECT: {proj_id} ---")
    
    # 1. Run pipeline through PO to Dev
    print("\n1. Running project workflow...")
    run_project_graph(proj_id, raw_input="Create a config validator utility in Python")
    
    state = get_project_state(proj_id)
    plan_dict = state.values.get("current_plan")
    
    print("\n2. Verifying Plan object in Graph State:")
    print(f"Current Plan Dict: {plan_dict}")
    
    assert plan_dict is not None, "State must contain 'current_plan'"
    assert "tasks" in plan_dict, "Plan dict must contain 'tasks'"
    assert len(plan_dict["tasks"]) > 0, "Plan must have at least 1 Task"
    
    first_task = plan_dict["tasks"][0]
    assert "file_path" in first_task, "Task must specify 'file_path'"
    assert "logical_task" in first_task, "Task must specify 'logical_task'"
    assert "atomic_tasks" in first_task, "Task must specify 'atomic_tasks'"
    assert len(first_task["atomic_tasks"]) > 0, "Task must contain AtomicTasks"
    
    first_atomic = first_task["atomic_tasks"][0]
    assert "atomic_task" in first_atomic, "AtomicTask must specify 'atomic_task'"

    # Re-validate model instantiation
    plan_obj = Plan(**plan_dict)
    print(f"\nSuccessfully validated Pydantic Plan object with {len(plan_obj.tasks)} tasks.")

    # 3. Resume and approve to finish
    print("\n3. Approving and completing run...")
    run_project_graph(proj_id, resume_command={"approved": True})
    
    print("\nALL STEP 16 STRUCTURED DATA CONTRACT CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_step16_structured_contracts()
