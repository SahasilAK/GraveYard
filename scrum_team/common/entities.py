from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class AtomicTask(BaseModel):
    atomic_task: str = Field(description="A concrete behavior change with implementation details, not a vague label.")
    additional_context: Optional[str] = Field(None, description="Inputs, outputs, examples, edge cases, and dependencies when applicable.")

class GeneratedCode(BaseModel):
    code: str = Field(description="Complete, runnable source file implementation.")
    status: Literal["complete", "blocked"] = Field(default="complete", description="Whether the implementation is complete or blocked by missing information.")
    notes: str = Field(default="", description="Explanation when blocked or relevant implementation notes.")
    validation_events: List[str] = Field(default_factory=list, description="Validation rejections and retry outcomes.")



class Task(BaseModel):
    file_path: str = Field(description="Target file path or feature area for the changes.")
    logical_task: str = Field(description="High-level description of what changes in this file/area.")
    atomic_tasks: List[AtomicTask] = Field(description="List of specific, scoped step-by-step changes.")

class DiffTask(BaseModel):
    file_path: str = Field(description="Target relative file path inside project directory.")
    original_code_snippet: str = Field(default="", description="Exact existing code being replaced, or empty string for new file/insertion.")
    task_description: str = Field(description="Description of the atomic code change.")
    new_code_snippet: str = Field(description="Target replacement code snippet.")

class Plan(BaseModel):
    tasks: List[Task] = Field(description="Ordered list of execution tasks for the backlog item.")
