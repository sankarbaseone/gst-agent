from enum import Enum
from pydantic import BaseModel
from typing import List

class VendorRiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class VendorRiskSummary(BaseModel):
    vendor_gstin: str
    total_invoices: int
    matched_count: int
    missing_in_2b_count: int
    risky_count: int
    total_taxable_value: float
    total_itc_amount: float
    risky_itc_amount: float
    vendor_risk_level: VendorRiskLevel
