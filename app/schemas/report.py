from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.vendor import VendorRiskLevel

# PHASE-1 LOCKED: REPORT SCHEMA
# Any changes to this schema must be reflected in BOTH JSON and PDF report formats.
# DO NOT add new GST sections (e.g., GSTR-1 vs 3B comparisons) in Phase-1.

class BusinessInfo(BaseModel):
    name: str = "-"
    gstin: str
    tenant_id: str

class ReconciliationSummary(BaseModel):
    total_invoices: int = 0
    matched_count: int = 0
    partial_match_count: int = 0
    missing_in_2b_count: int = 0
    risky_itc_count: int = 0
    total_taxable_value: float = 0.0
    total_itc_available: float = 0.0
    risky_itc_amount: float = 0.0

class VendorSummaryItem(BaseModel):
    vendor_gstin: str
    total_invoices: int = 0
    risky_count: int = 0
    risky_itc_amount: float = 0.0
    risk_level: VendorRiskLevel = VendorRiskLevel.LOW

class InvoiceDetail(BaseModel):
    invoice_number: str
    gstin: str
    status: str
    taxable_value: float = 0.0
    itc_amount: float = 0.0
    suggested_action: str = "-"

class RiskAssessment(BaseModel):
    finding_summary: str = "No critical risks identified"
    risk_score: float = 0.0  # 0 to 100
    recommendation: str = "-"

class ReportAudit(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_id: str
    reconciliation_version: str = "1.0.0"
    data_sources: List[str] = ["User_Upload", "Government_Portal_Mock"]

class ReportResponse(BaseModel):
    business: BusinessInfo
    summary: ReconciliationSummary
    vendor_summary: List[VendorSummaryItem] = []
    invoice_details: List[InvoiceDetail] = []
    risk_assessment: RiskAssessment
    audit: ReportAudit
