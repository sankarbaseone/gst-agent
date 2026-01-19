from fastapi import APIRouter, HTTPException, Header
from app.db.memory import APP_STATE
from app.schemas.report import ReportResponse, BusinessInfo, ReconciliationSummary, VendorSummaryItem, InvoiceDetail, RiskAssessment, ReportAudit
from app.schemas.reconciliation import ReconciliationStatus
from datetime import datetime
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/reports/gst-risk", response_model=ReportResponse)
async def get_gst_risk_report(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    logger.info(f"JSON Report Generation STARTED for tenant: {x_tenant_id}")
    
    # 1. Fetch Stored Data
    data = APP_STATE.get(x_tenant_id)
    if not data or not data.get("reconciliation"):
        raise HTTPException(status_code=404, detail="No reconciliation results found for this session.")

    results = data["reconciliation"]
    invoices = data.get("invoices", [])
    vendor_summary_data = data.get("vendor_summary", [])

    # 2. Aggregate Summary Metrics
    counts = {"MATCHED": 0, "PARTIAL_MATCH": 0, "MISSING_IN_2B": 0, "RISKY_ITC": 0}
    total_taxable = 0.0
    total_itc = 0.0
    risky_itc_amt = 0.0

    for r in results:
        status_key = r["status"].name if hasattr(r["status"], "name") else str(r["status"])
        counts[status_key] = counts.get(status_key, 0) + 1
    
    for inv in invoices:
        total_taxable += float(inv.taxable_value)
        itc = float(inv.igst + inv.cgst + inv.sgst)
        total_itc += itc
        
    # Risky ITC calculation (from results)
    for r in results:
        if r["status"] == ReconciliationStatus.RISKY_ITC or r["status"] == ReconciliationStatus.MISSING_IN_2B:
             # Find matching invoice for ITC amount
             inv = next((i for i in invoices if i.invoice_number == r["invoice_number"]), None)
             if inv:
                 risky_itc_amt += float(inv.igst + inv.cgst + inv.sgst)

    # 3. Map Vendor Summary
    vendors = []
    for v in vendor_summary_data:
        vendors.append(VendorSummaryItem(
            vendor_gstin=v["vendor_gstin"],
            total_invoices=int(v.get("total_invoices", 0)),
            risky_count=int(v.get("risky_count", 0)),
            risky_itc_amount=float(v.get("risky_itc_amount", 0.0)),
            risk_level=v.get("vendor_risk_level", "LOW")
        ))

    # 4. Map Invoice Details
    invoice_details = []
    for r in results[:100]: # Limit to top 100 for JSON response
        inv = next((i for i in invoices if i.invoice_number == r["invoice_number"]), None)
        invoice_details.append(InvoiceDetail(
            invoice_number=r["invoice_number"],
            gstin=r["gstin"],
            status=r["status"].value if hasattr(r["status"], "value") else str(r["status"]),
            taxable_value=float(inv.taxable_value) if inv else 0.0,
            itc_amount=float(inv.igst + inv.cgst + inv.sgst) if inv else 0.0,
            suggested_action=r.get("suggested_action", "-")
        ))

    # 5. Risk Assessment (Deterministic logic placeholder)
    high_risk_vendors = [v for v in vendors if v.risk_level == "HIGH"]
    risk_score = 100.0 if not results else (len(high_risk_vendors) / len(vendors) * 100 if vendors else 0.0)
    
    assessment = RiskAssessment(
        finding_summary=f"Found {counts['RISKY_ITC']} risky invoices and {len(high_risk_vendors)} high-risk vendors." if high_risk_vendors else "No critical risks identified.",
        risk_score=round(risk_score, 2),
        recommendation="Review high-risk vendors before filing." if high_risk_vendors else "Proceed with filing."
    )

    # 6. Build Final Response
    report = ReportResponse(
        business=BusinessInfo(
            gstin=invoices[0].gstin if invoices else "-",
            tenant_id=x_tenant_id
        ),
        summary=ReconciliationSummary(
            total_invoices=len(invoices),
            matched_count=counts["MATCHED"],
            partial_match_count=counts["PARTIAL_MATCH"],
            missing_in_2b_count=counts["MISSING_IN_2B"],
            risky_itc_count=counts["RISKY_ITC"],
            total_taxable_value=round(total_taxable, 2),
            total_itc_available=round(total_itc, 2),
            risky_itc_amount=round(risky_itc_amt, 2)
        ),
        vendor_summary=vendors,
        invoice_details=invoice_details,
        risk_assessment=assessment,
        audit=ReportAudit(
            report_id=str(uuid.uuid4())
        )
    )

    return report
