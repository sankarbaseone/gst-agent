from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from app.db.memory import APP_STATE
from app.schemas.report import ReportResponse, BusinessInfo, ReconciliationSummary, VendorSummaryItem, InvoiceDetail, RiskAssessment, ReportAudit
from app.schemas.reconciliation import ReconciliationStatus
from app.schemas.audit import AuditLogEntry, AuditStatus
from app.core.audit import audit_repo
from datetime import datetime
import uuid
import logging
import io
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter()
logger = logging.getLogger(__name__)

async def internal_get_report_data(x_tenant_id: str) -> ReportResponse:
    """Helper to aggregate report data for both JSON and PDF endpoints."""
    data = APP_STATE.get(x_tenant_id)
    if not data or not data.get("reconciliation"):
        raise HTTPException(status_code=404, detail="No reconciliation results found for this session.")

    results = data["reconciliation"]
    invoices = data.get("invoices", [])
    vendor_summary_data = data.get("vendor_summary", [])

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
        
    for r in results:
        if r["status"] == ReconciliationStatus.RISKY_ITC or r["status"] == ReconciliationStatus.MISSING_IN_2B:
             inv = next((i for i in invoices if i.invoice_number == r["invoice_number"]), None)
             if inv:
                 risky_itc_amt += float(inv.igst + inv.cgst + inv.sgst)

    vendors = []
    for v in vendor_summary_data:
        vendors.append(VendorSummaryItem(
            vendor_gstin=v["vendor_gstin"],
            total_invoices=int(v.get("total_invoices", 0)),
            risky_count=int(v.get("risky_count", 0)),
            risky_itc_amount=float(v.get("risky_itc_amount", 0.0)),
            risk_level=v.get("vendor_risk_level", "LOW")
        ))

    invoice_details = []
    for r in results[:100]:
        inv = next((i for i in invoices if i.invoice_number == r["invoice_number"]), None)
        invoice_details.append(InvoiceDetail(
            invoice_number=r["invoice_number"],
            gstin=r["gstin"],
            status=r["status"].value if hasattr(r["status"], "value") else str(r["status"]),
            taxable_value=float(inv.taxable_value) if inv else 0.0,
            itc_amount=float(inv.igst + inv.cgst + inv.sgst) if inv else 0.0,
            suggested_action=r.get("suggested_action", "-")
        ))

    high_risk_vendors = [v for v in vendors if v.risk_level == "HIGH"]
    risk_score = 100.0 if not results else (len(high_risk_vendors) / len(vendors) * 100 if vendors else 0.0)
    
    assessment = RiskAssessment(
        finding_summary=f"Found {counts['RISKY_ITC']} risky invoices and {len(high_risk_vendors)} high-risk vendors." if high_risk_vendors else "No critical risks identified.",
        risk_score=round(risk_score, 2),
        recommendation="Review high-risk vendors before filing." if high_risk_vendors else "Proceed with filing."
    )

    return ReportResponse(
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
        audit=ReportAudit(report_id=str(uuid.uuid4()))
    )

@router.get("/reports/gst-risk", response_model=ReportResponse)
async def get_gst_risk_report(x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    logger.info(f"JSON Report requested for tenant: {x_tenant_id}")
    return await internal_get_report_data(x_tenant_id)

@router.get("/reports/gst-risk/pdf")
async def get_gst_risk_pdf_report(x_tenant_id: str = Header(..., alias="X-Tenant-ID")):
    logger.info(f"PDF Report Generation STARTED for tenant: {x_tenant_id}")
    
    try:
        report = await internal_get_report_data(x_tenant_id)
    except HTTPException as e:
        raise e

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # 1. Header & Business Info
    elements.append(Paragraph("GST Reconciliation & Risk Report", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Tenant ID:</b> {report.business.tenant_id}", styles['Normal']))
    elements.append(Paragraph(f"<b>GSTIN:</b> {report.business.gstin}", styles['Normal']))
    elements.append(Paragraph(f"<b>Generated:</b> {report.audit.generated_at.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # 2. Risk Assessment
    elements.append(Paragraph("Risk Assessment", styles['Heading2']))
    elements.append(Paragraph(f"<b>Risk Score:</b> {report.risk_assessment.risk_score}/100", styles['Normal']))
    elements.append(Paragraph(f"<b>Finding Summary:</b> {report.risk_assessment.finding_summary}", styles['Normal']))
    elements.append(Paragraph(f"<b>Recommendation:</b> {report.risk_assessment.recommendation}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # 3. Summary Table
    elements.append(Paragraph("Reconciliation Summary", styles['Heading2']))
    summary_data = [
        ["Metric", "Value"],
        ["Total Invoices", str(report.summary.total_invoices)],
        ["Matched", str(report.summary.matched_count)],
        ["Missing in GSTR-2B", str(report.summary.missing_in_2b_count)],
        ["Risky ITC Count", str(report.summary.risky_itc_count)],
        ["Total ITC Available", f"Rs. {report.summary.total_itc_available:.2f}"],
        ["Risky ITC Amount", f"Rs. {report.summary.risky_itc_amount:.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[200, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 24))

    # 4. Mandatory Footer
    elements.append(Spacer(1, 48))
    footer_text = "This report is for internal compliance only. Generated via GST Trust Authoritative Rules Engine."
    elements.append(Paragraph(footer_text, ParagraphStyle(name='Footer', fontSize=8, textColor=colors.grey, alignment=1)))

    try:
        doc.build(elements)
    except Exception as e:
        logger.error(f"PDF Build Failed: {str(e)}")
        raise HTTPException(status_code=500, detail="PDF generation failed during document build.")

    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    # Audit Logging
    audit_repo.save(AuditLogEntry(
        endpoint="/reports/gst-risk/pdf",
        method="GET",
        action_type="PDF_DOWNLOAD",
        tenant_id=x_tenant_id,
        output_hash=pdf_hash,
        status=AuditStatus.SUCCESS
    ))

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=GST_Trust_Report_{x_tenant_id[:8]}.pdf",
            "Content-Length": str(len(pdf_bytes))
        }
    )
