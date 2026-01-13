import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.memory import APP_STATE
from app.schemas.invoice import Invoice
from app.core.reconciliation import reconcile_invoice
from app.core.vendor_aggregation import aggregate_vendor_risk
import asyncio
from app.api.reports import get_gst_risk_report

async def test_pdf_with_vendor_summary():
    tenant_id = "test-tenant-summary"
    
    # 1. Create dummy data
    invoices = [
        Invoice(gstin="29ABCDE1234F1Z5", invoice_no="INV01", invoice_date="2023-10-01", taxable_value=5000, cgst=450, sgst=450, igst=0),
        Invoice(gstin="29ABCDE1234F1Z5", invoice_no="INV02", invoice_date="2023-10-01", taxable_value=12000, cgst=1080, sgst=1080, igst=0),
        Invoice(gstin="99XYZDW5678Q1Z2", invoice_no="INV03", invoice_date="2023-10-01", taxable_value=2000, cgst=180, sgst=180, igst=0)
    ]
    
    results = [reconcile_invoice(inv, i) for i, inv in enumerate(invoices)]
    vendor_summary = aggregate_vendor_risk(invoices, results)
    
    # 2. Populate APP_STATE
    APP_STATE[tenant_id] = {
        "invoices": invoices,
        "reconciliation": results,
        "vendor_summary": [v.dict() for v in vendor_summary]
    }
    
    print(f"Aggregated {len(vendor_summary)} vendors.")
    for v in vendor_summary:
        print(f"Vendor: {v.vendor_gstin}, Risk: {v.vendor_risk_level}")
    
    # 3. Generate PDF
    print("Generating PDF...")
    response = await get_gst_risk_report(x_tenant_id=tenant_id)
    
    # Use await to get the body from StreamingResponse
    content = b""
    async for chunk in response.body_iterator:
        content += chunk
    
    output_path = "test_vendor_summary.pdf"
    with open(output_path, "wb") as f:
        f.write(content)
    
    print(f"PDF generated at: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    asyncio.run(test_pdf_with_vendor_summary())
