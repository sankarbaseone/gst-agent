from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from app.db.memory import APP_STATE
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from datetime import datetime

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/reports/gst-risk")
async def get_gst_risk_report(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    logger.info(f"PDF Generation STARTED for tenant: {x_tenant_id}")
    # This report renders existing reconciliation results only. 
    # Reconciliation logic MUST NOT be added here.
    
    # 1. Fetch Stored Data (Assertion: No recomputation allowed)
    data = APP_STATE.get(x_tenant_id)
    if not data or not data.get("reconciliation"):
        raise HTTPException(status_code=404, detail="No reconciliation results found for this session.")

    results = data["reconciliation"]
    
    # 2. Build PDF Document (Representational Only)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("GST Reconciliation & Risk Report (Pre-Filing)", styles['Title']))
    elements.append(Spacer(1, 12))

    # Metadata
    elements.append(Paragraph(f"<b>Tenant ID:</b> {x_tenant_id}", styles['Normal']))
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Summary Section (Simple aggregation of EXISTING results)
    counts = {"MATCHED": 0, "PARTIAL_MATCH": 0, "MISSING_IN_2B": 0, "RISKY_ITC": 0}
    for r in results:
        status_key = r["status"].name if hasattr(r["status"], "name") else str(r["status"])
        counts[status_key] = counts.get(status_key, 0) + 1

    summary_data = [
        ["Status", "Count"],
        ["Matched", counts["MATCHED"]],
        ["Partial Match", counts["PARTIAL_MATCH"]],
        ["Missing in GSTR-2B", counts["MISSING_IN_2B"]],
        ["Risky ITC", counts["RISKY_ITC"]]
    ]
    summary_table = Table(summary_data, colWidths=[200, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(Paragraph("Summary Results", styles['Heading2']))
    elements.append(summary_table)
    elements.append(Spacer(1, 24))

    # Detailed Table
    table_data = [["Invoice No", "GSTIN", "Status", "Action"]]
    for r in results[:100]: 
        status_val = r["status"].value if hasattr(r["status"], "value") else str(r["status"])
        table_data.append([
            r["invoice_number"],
            r["gstin"],
            status_val,
            r["suggested_action"]
        ])

    table = Table(table_data, repeatRows=1, colWidths=[100, 100, 100, 200])
    table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(Paragraph("Detailed Invoices (Top 100)", styles['Heading2']))
    elements.append(table)
    
    # Mandatory Footer
    elements.append(Spacer(1, 48))
    footer_text = "This report provides reconciliation insights only. It does not constitute tax advice and does not file GST returns."
    elements.append(Paragraph(footer_text, ParagraphStyle(name='Footer', fontSize=8, textColor=colors.grey, alignment=1)))

    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=GST_Risk_Report_{x_tenant_id[:8]}.pdf"}
    )
