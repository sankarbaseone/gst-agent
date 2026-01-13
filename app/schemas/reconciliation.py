from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISSING_IN_2B = "MISSING_IN_2B"
    RISKY_ITC = "RISKY_ITC"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class ReconciliationResult(BaseModel):
    invoice_number: str
    gstin: str
    status: ReconciliationStatus
    diffs: Dict[str, Any] = Field(default_factory=dict)
    remarks: Optional[str] = None
