from typing import Dict, Any

# AUTHORITATIVE GLOBAL STORE – DO NOT DUPLICATE
# Structure: { tenant_id: { "invoices": [], "reconciliation": [], "timestamp": "" } }
# PHASE-1 LOCKED: In-memory store only. 
# DO NOT add persistent database migrations or multi-tenant indexing in Phase-1.
APP_STATE: Dict[str, Any] = {}
