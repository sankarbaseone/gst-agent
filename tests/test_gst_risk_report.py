import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.vendor import VendorRiskLevel
import uuid

client = TestClient(app)

@pytest.fixture
def sample_csv():
    """Real sample data for GST reconciliation."""
    return (
        "invoice_no,gstin,taxable_value,igst,cgst,sgst,invoice_date\n"
        "INV-2024-001,27AAAAA0000A1Z5,1000.00,180.00,0,0,2024-01-01\n"
        "INV-2024-002,27BBBBB1111B1Z5,2000.00,0,90.00,90.00,2024-01-02\n"
        "INV-2024-003,27CCCCC2222C1Z5,1500.00,270.00,0,0,2024-01-03\n"
    )

def test_gst_risk_report_full_flow(sample_csv):
    """
    Test the full flow: Upload -> Populate State -> Generate JSON Report.
    Validates shape, types, and constraints.
    """
    tenant_id = f"test-tenant-{uuid.uuid4().hex[:8]}"
    headers = {"X-Tenant-ID": tenant_id, "X-Plan": "PRO"}
    
    # 1. Ingest Data (Real logic, no mocks as per Requirement)
    files = {"file": ("test_data.csv", sample_csv, "text/csv")}
    upload_res = client.post("/invoices/upload", files=files, headers=headers)
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"

    # 2. Retrieve Report
    response = client.get("/reports/gst-risk", headers={"X-Tenant-ID": tenant_id})
    assert response.status_code == 200
    report = response.json()

    # Requirement 1 & 4: Validate required sections and shape
    expected_sections = ["business", "summary", "vendor_summary", "invoice_details", "risk_assessment", "audit"]
    for section in expected_sections:
        assert section in report, f"Missing required section: {section}"

    # Requirement 2: Assert numeric fields are numbers (not strings or null)
    summary = report["summary"]
    numeric_summary_fields = [
        "total_invoices", "matched_count", "partial_match_count", 
        "missing_in_2b_count", "risky_itc_count", "total_taxable_value", 
        "total_itc_available", "risky_itc_amount"
    ]
    for field in numeric_summary_fields:
        val = summary[field]
        assert isinstance(val, (int, float)), f"Field {field} is {type(val)}, expected number"
        assert val is not None, f"Field {field} is None"

    # Requirement 3: Assert vendor risk levels
    valid_risk_levels = {level.value for level in VendorRiskLevel}
    assert len(report["vendor_summary"]) > 0
    for vendor in report["vendor_summary"]:
        assert vendor["risk_level"] in valid_risk_levels, f"Invalid risk level: {vendor['risk_level']}"
        # Also check numeric types in vendor summary
        assert isinstance(vendor["total_invoices"], int)
        assert isinstance(vendor["risky_itc_amount"], (int, float))

    # Validate Invoice Details
    assert len(report["invoice_details"]) > 0
    for inv in report["invoice_details"]:
        assert isinstance(inv["taxable_value"], (int, float))
        assert isinstance(inv["itc_amount"], (int, float))
        assert isinstance(inv["status"], str)

    # Validate Audit
    assert "report_id" in report["audit"]
    assert "generated_at" in report["audit"]

def test_gst_risk_report_not_found():
    """Test behavior when no data exists for tenant."""
    response = client.get("/reports/gst-risk", headers={"X-Tenant-ID": "non-existent-tenant"})
    assert response.status_code == 404
    assert "detail" in response.json()

def test_gst_risk_report_safe_defaults(sample_csv):
    """
    Test that optional/aggregated fields return safe defaults.
    """
    tenant_id = f"test-tenant-alt-{uuid.uuid4().hex[:8]}"
    # Upload minimal data
    files = {"file": ("min.csv", sample_csv, "text/csv")}
    client.post("/invoices/upload", files=files, headers={"X-Tenant-ID": tenant_id, "X-Plan": "BASIC"})
    
    response = client.get("/reports/gst-risk", headers={"X-Tenant-ID": tenant_id})
    report = response.json()
    
    # Check risk assessment defaults
    assert report["risk_assessment"]["risk_score"] >= 0
    assert isinstance(report["risk_assessment"]["finding_summary"], str)
    assert report["risk_assessment"]["recommendation"] != ""
