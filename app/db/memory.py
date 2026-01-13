from typing import Dict, Any

# AUTHORITATIVE GLOBAL STORE – DO NOT DUPLICATE
# Structure: { tenant_id: { "invoices": [], "reconciliation": [], "timestamp": "" } }
APP_STATE: Dict[str, Any] = {}
