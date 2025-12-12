from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class AnalyzeRequest(BaseModel):
    employee_id: Optional[str] = ""
    account: str
    industry: str
    industry_subcategory: Optional[str] = ""
    problem: str
    context: Dict[str, Any] = Field(default_factory=dict)
    multiround_convo: Optional[int] = 1


class AnalyzeResponse(BaseModel):
    output_text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class Feedback(BaseModel):
    Employee_id: str = ""
    Feedback: str = ""
    FeedbackType: str = ""
    OffDefinitions: str = ""
    Suggestions: str = ""
    Account: str = ""
    Industry: str = ""
    ProblemStatement: str = ""
    Agent: str = ""
    Section: Optional[str] = ""
    Timestamp: Optional[str] = None
