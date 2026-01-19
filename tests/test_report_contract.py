from fastapi.testclient import TestClient
from app.main import app
import csv
import io

client = TestClient(app)

def test_report_contract():
    tenant_id = "test-tenant-report"
    
    # 1. Upload Invoices to populate APP_STATE
    csv_content = "invoice_no,gstin,taxable_value,igst,cgst,sgst,invoice_date\nINV001,27AAAAA0000A1Z5,1000,180,0,0,2023-10-01\nINV002,27BBBBB1111B1Z5,2000,0,90,90,2023-10-02"
    files = {"file": ("test_invoices.csv", csv_content, "text/csv")}
    headers = {"X-Tenant-ID": tenant_id, "X-Plan": "PRO"}
    
    upload_res = client.post("/invoices/upload", files=files, headers=headers)
    if upload_res.status_code != 200:
        print(f"Upload failed: {upload_res.status_code}")
        print(upload_res.text)
    assert upload_res.status_code == 200
    
    # 2. Call Report Endpoint
    response = client.get("/reports/gst-risk", headers={"X-Tenant-ID": tenant_id})
    assert response.status_code == 200
    
    data = response.json()
    
    # Check Required Top-level keys
    required_keys = ["business", "summary", "vendor_summary", "invoice_details", "risk_assessment", "audit"]
    for key in required_keys:
        assert key in data
        
    # Check Numeric Fields (Summary)
    summary = data["summary"]
    assert isinstance(summary["total_invoices"], int)
    assert isinstance(summary["total_taxable_value"], (int, float))
    assert isinstance(summary["total_itc_available"], (int, float))
    
    # Check safe defaults in risk assessment
    assert "finding_summary" in data["risk_assessment"]
    assert isinstance(data["risk_assessment"]["risk_score"], (int, float))
    
    # Check Audit
    assert "report_id" in data["audit"]
    assert "generated_at" in data["audit"]
    
    print("\nPASSED: Report contract validation successful.")

if __name__ == "__main__":
    test_report_contract()
