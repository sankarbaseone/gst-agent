from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.reports import router as reports_router
from app.api.invoices import router as invoices_router
from app.db.memory import APP_STATE
import uuid

# Create a clean app WITHOUT AuditMiddleware for isolation test
app = FastAPI()
app.include_router(invoices_router)
app.include_router(reports_router)

client = TestClient(app)

def test_pdf_endpoint_logic_isolation():
    tenant_id = f"iso-test-{uuid.uuid4().hex[:6]}"
    
    # 1. Setup Data
    csv_content = "invoice_no,gstin,taxable_value,igst,cgst,sgst,invoice_date\nISO-1,27AAAAA0000A1Z5,100.0,18.0,0,0,2024-01-01"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    client.post("/invoices/upload", files=files, headers={"X-Tenant-ID": tenant_id, "X-Plan": "PRO"})
    
    # 2. Trigger PDF Download
    response = client.get("/reports/gst-risk/pdf", headers={"X-Tenant-ID": tenant_id})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    
    print("\nPASSED: Isolated PDF endpoint logic is correct.")

if __name__ == "__main__":
    test_pdf_endpoint_logic_isolation()
