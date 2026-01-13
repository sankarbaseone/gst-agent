from fastapi.testclient import TestClient
from app.main import app
from app.core.audit import audit_repo
from app.schemas.audit import AuditStatus
import hashlib

client = TestClient(app)

def test_audit_hardening():
    print("Testing Audit Logging Hardening...")
    audit_repo._storage.clear()

    # 1. Test GET /health (Empty Body)
    print("1. Testing GET /health...")
    response = client.get("/health")
    assert response.status_code == 200
    
    health_log = next((l for l in audit_repo.get_all() if l.endpoint == "/health"), None)
    if not health_log:
        print("FAILED: No audit log for /health. Middleware might be failing silently.")
        # We can stop here or verify more
    else:
        print("PASSED: /health logged.")
        # Check determinism for empty body
        # Current implementation sets input_hash to None if body is empty.
        # User constraint: "input_hash (SHA-256 of request body)" - strict interpretation usually means hash(b"")
        # But let's see what we get.
        print(f"   Input Hash: {health_log.input_hash}")
        # empty_hash = hashlib.sha256(b"").hexdigest() -> e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        assert health_log.input_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert health_log.action_type == "HEALTH_CHECK"
        assert health_log.status == AuditStatus.SUCCESS

    # 2. Test Invalid Endpoint (404)
    # Middleware logic: status defaults to FAILURE.
    # response.status_code < 300 checks for SUCCESS.
    # 404 is >= 300, so should be FAILURE? Or is 404 just a "SUCCESS"ful response of "Not Found"?
    # Typically API logging considers 4xx as client errors but successful *processing*.
    # Re-reading req: "status (SUCCESS / FAILURE)". usually means Did the system crash?
    # But code `if 200 <= status < 300` implies 4xx is FAILURE.
    print("\n2. Testing 404...")
    client.get("/non-existent-endpoint")
    logs = audit_repo.get_all()
    log404 = next((l for l in logs if l.endpoint == "/non-existent-endpoint"), None)
    
    if log404:
        print(f"PASSED: 404 logged. Status: {log404.status}")
    else:
        print("FAILED: 404 NOT logged.")

if __name__ == "__main__":
    test_audit_hardening()
