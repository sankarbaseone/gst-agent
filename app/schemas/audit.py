from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum

class AuditStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

class AuditLogEntry(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    endpoint: str
    method: str
    action_type: str
    actor: str = "system"
    tenant_id: str
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    status: AuditStatus
