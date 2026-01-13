from fastapi.testclient import TestClient
from app.main import app
from app.schemas.reconciliation import ReconciliationStatus

client = TestClient(app)

def test_explain_fallback():
    print("Testing AI Explanation Fallback (No API Key)...")
    payload = {
        "invoice_number": "INV-001",
        "gstin": "29ABCDE1234F1Z5",
        "status": "PARTIAL_MATCH",
        "factual_diffs": {
            "taxable_value": {"customer": 1000.0, "gstr2b": 1005.0} # $5 diff
        }
    }
    
    response = client.post("/explain-mismatch", json=payload)
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}")
        print(response.content)
        return

    data = response.json()
    
    # 1. Assert Fallback occurs (since we have no API key)
    assert data["explanation"] == "Automated explanation unavailable. Please review manually."
    assert data["root_cause"] == "System Limitation"
    
    # 2. Assert Status is preserved
    assert data["original_status"] == "PARTIAL_MATCH"
    
    print("PASSED: Fallback triggered and status preserved.")

if __name__ == "__main__":
    test_explain_fallback()
