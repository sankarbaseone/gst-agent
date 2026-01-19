from fastapi.testclient import TestClient
from app.main import app
from app.core.audit import audit_repo
import uuid

client = TestClient(app)

def test_pdf_report_download():
    tenant_id = f"pdf-test-{uuid.uuid4().hex[:6]}"
    
    # 1. Setup Data for Tenant
    csv_content = "invoice_no,gstin,taxable_value,igst,cgst,sgst,invoice_date\nINV-P1,27AAAAA0000A1Z5,100.0,18.0,0,0,2024-01-01"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    client.post("/invoices/upload", files=files, headers={"X-Tenant-ID": tenant_id, "X-Plan": "PRO"})
    
    # 2. Trigger PDF Download
    response = client.get("/reports/gst-risk/pdf", headers={"X-Tenant-ID": tenant_id})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "GST_Trust_Report" in response.headers["content-disposition"]
    
    # Verify Content (PDF Header)
    assert response.content.startswith(b"%PDF")
    
    # 3. Verify Audit Trail
    logs = audit_repo.get_all()
    pdf_log = next((l for l in logs if l.endpoint == "/reports/gst-risk/pdf"), None)
    assert pdf_log is not None
    assert pdf_log.action_type == "PDF_DOWNLOAD"
    assert pdf_log.output_hash is not None
    assert pdf_log.tenant_id == tenant_id
    
    print("\nPASSED: PDF binary streaming and audit verification successful.")

if __name__ == "__main__":
    test_pdf_report_download()
