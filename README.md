# GST Trust — Compliance-Grade GST Reconciliation

Phase-1 **Revenue-Ready Implementation** of deterministic GST reconciliation
with strict tenant isolation, audit logging, and regulator-safe reporting.

---

## Core Features

- **Deterministic Reconciliation**  
  Single authoritative rules engine for matching Customer invoices
  against Government (GSTR-2B) data.

- **Strict Tenant Isolation**  
  Tenant-scoped sessions using server-generated identifiers
  stored in HttpOnly cookies.

- **Audit Logging**  
  Immutable, append-only audit logs with cryptographic payload hashing.

- **Revenue Ready**  
  Enforced usage limits (100 / 500 / 1000 invoices) based on plan selection.

- **Reporting**  
  Downloadable, CA-friendly PDF GST Risk Reports.

---

## Architectural Invariant (Important)

- There is **exactly one authoritative reconciliation engine**
- Reconciliation is executed once at ingestion
- UI dashboards and PDF reports consume the **same precomputed results**
- No recomputation occurs in UI or reporting layers

This invariant is critical for auditability and compliance.

---

## Running the Application Locally

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

---

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (macOS / Linux)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate
    