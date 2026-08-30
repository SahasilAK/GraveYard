from pydantic import BaseModel, Field
from typing import List

class TaskItemSchema(BaseModel):
    id: str = Field(description="Unique task identifier, e.g. TASK-1")
    title: str = Field(description="Short summary of the task")
    description: str = Field(description="Detailed requirements for the task")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Criteria for completion")

class BacklogSchema(BaseModel):
    items: List[TaskItemSchema] = Field(description="Prioritized list of task items")
