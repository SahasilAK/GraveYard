from pydantic import BaseModel, Field
from typing import List, Optional

class BriefSchema(BaseModel):
    goal: str = Field(description="The primary objective of the project/task.")
    scope: List[str] = Field(description="List of features or work items in scope.")
    constraints: List[str] = Field(description="Technical or organizational constraints.")
    acceptance_criteria: List[str] = Field(description="Key metrics/conditions for completion.")
    priorities: List[str] = Field(description="Order of work items/features.")
