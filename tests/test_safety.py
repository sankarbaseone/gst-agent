from fastapi.testclient import TestClient
from app.main import app
from app.core.audit import audit_repo
import io

client = TestClient(app)

def create_csv_content(rows_count):
    headers = "gstin,invoice_no,invoice_date,taxable_value,cgst,sgst,igst"
    rows = [headers]
    for i in range(rows_count):
        rows.append(f"29ABCDE1234F1Z5,INV-{i},2023-10-01,1000,90,90,0")
    return "\n".join(rows)

def test_safety_features():
    print("Testing Revenue Safety & Tenant Isolation...")
    audit_repo._storage.clear()

    # 1. Tenant Isolation: Missing Header
    print("\n1. Testing Missing Tenant Header (Invoices)...")
    files = {'file': ('test.csv', create_csv_content(1), 'text/csv')}
    response = client.post("/invoices/upload", files=files)
    
    # Check 400 rejection (from middleware logic + endpoint validation)
    # Endpoint defines Header dependency ? actually middleware might pass it, but FastAPI strict Header check runs first or after?
    # Middleware logic: "if not tenant_id: try ... return JSONResponse(status_code=400)"
    # Middleware runs BEFORE endpoint. So it should return 400 "Missing tenant identifier".
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing tenant identifier"

    # Verify Audit Log
    logs = audit_repo.get_all()
    rejection_log = logs[-1]
    print(f"   Log Tenant: {rejection_log.tenant_id}")
    assert rejection_log.tenant_id == "MISSING"
    assert rejection_log.status == "FAILURE"

    # 2. Usage Limits: BASIC Plan (Default)
    # Limit is 100. Let's upload 101.
    print("\n2. Testing Usage Limits (BASIC - 101 rows)...")
    files = {'file': ('limit_test.csv', create_csv_content(101), 'text/csv')}
    # Provide Tenant ID but NO Plan (defaults to BASIC)
    headers = {"X-Tenant-ID": "tenant-1"}
    response = client.post("/invoices/upload", files=files, headers=headers)
    
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")
    assert response.status_code == 413
    assert "Invoice limit exceeded" in response.json()["detail"]

    # 3. Usage Limits: PRO Plan (Allows 500)
    print("\n3. Testing Usage Limits (PRO - 101 rows)...")
    files = {'file': ('limit_test.csv', create_csv_content(101), 'text/csv')}
    headers = {"X-Tenant-ID": "tenant-1", "X-Plan": "PRO"}
    response = client.post("/invoices/upload", files=files, headers=headers)
    
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200

    # 4. Error Hardening: Invalid CSV
    print("\n4. Testing Error Hardening (Invalid CSV)...")
    # Missing required column
    bad_csv = "gstin,invoice_no,invoice_date\n29ABCDE1234F1Z5,INV-1,2023-10-01"
    files = {'file': ('bad.csv', bad_csv, 'text/csv')}
    headers = {"X-Tenant-ID": "tenant-1"}
    response = client.post("/invoices/upload", files=files, headers=headers)
    
    print(f"   Status: {response.status_code}")
    print(f"   Body: {response.json()}")
    assert response.status_code == 400
    assert "Missing required columns" in response.json()["detail"]

if __name__ == "__main__":
    test_safety_features()
