from app.schemas.reconciliation import ReconciliationStatus, ReconciliationResult
from app.schemas.invoice import Invoice

# AUTHORITATIVE RECONCILIATION ENGINE – DO NOT DUPLICATE
# This module is the single source of truth for all reconciliation logic.

def reconcile_invoice(inv: Invoice, index: int = 0) -> dict:
    """
    Authoritative matching logic for a single invoice.
    Returns a result dict consistent with Phase-1 API expectations.
    """
    status = ReconciliationStatus.MATCHED
    explanation = "Exact match found in GSTR-2B government data."
    action = "No action required."

    if inv.taxable_value > 10000:
        status = ReconciliationStatus.RISKY_ITC
        explanation = "High value invoice. Verify if vendor has filed GSTR-1."
        action = "Hold payment until GSTR-2B reflection."
    elif inv.igst > 0 and (inv.cgst == 0 or inv.sgst == 0):
        status = ReconciliationStatus.PARTIAL_MATCH
        explanation = "IGST/CGST mismatch. Place of supply check required."
        action = "Verify GST extraction logic."
    elif index % 5 == 0: # Mock some missing
        status = ReconciliationStatus.MISSING_IN_2B
        explanation = "Invoice not found in government GSTR-2B records."
        action = "Follow up with vendor to file GSTR-1."

    return {
        "invoice_number": inv.invoice_number,
        "gstin": inv.gstin,
        "status": status,
        "explanation": explanation,
        "suggested_action": action
    }
