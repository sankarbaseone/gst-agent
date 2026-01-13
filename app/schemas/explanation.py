from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.schemas.reconciliation import ReconciliationStatus

class ExplainRequest(BaseModel):
    invoice_number: str
    gstin: str
    status: ReconciliationStatus
    factual_diffs: Dict[str, Any]

class ExplainResponse(BaseModel):
    explanation: str
    root_cause: str
    suggested_action: str
    original_status: ReconciliationStatus
