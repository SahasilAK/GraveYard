from typing import TypedDict, List, Optional, Dict, Any, Literal
from pydantic import BaseModel

class TaskItem(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    status: Literal["todo", "in_progress", "in_review", "qa", "done", "failed"] = "todo"

class ScrumTeamState(TypedDict):
    project_id: str
    brief: Optional[str]
    backlog: List[TaskItem]
    current_task_id: Optional[str]
    current_plan: Optional[Dict[str, Any]]
    completed_task_ids: Optional[List[str]]
    in_progress_task_id: Optional[str]
    task_status_map: Optional[Dict[str, str]]
    dev_output: Optional[Dict[str, Any]]
    qa_smoke_results: Optional[Dict[str, Any]]
    qa_full_results: Optional[Dict[str, Any]]
    human_feedback: Optional[str]
    raw_input: Optional[str]
    status: str  # e.g., "planning", "development", "qa", "paused", "finished"
