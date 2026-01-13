from typing import List, Dict, Any
from app.schemas.vendor import VendorRiskSummary, VendorRiskLevel
from app.schemas.reconciliation import ReconciliationStatus
from app.schemas.invoice import Invoice

def aggregate_vendor_risk(invoices: List[Invoice], reconciliation_results: List[Dict[str, Any]]) -> List[VendorRiskSummary]:
    """
    Aggregates existing reconciliation results by Vendor GSTIN.
    DOES NOT perform any new reconciliation logic.
    """
    vendor_map: Dict[str, Dict[str, Any]] = {}
    
    for inv, result in zip(invoices, reconciliation_results):
        gstin = inv.gstin
        status_key = result["status"].name if hasattr(result["status"], "name") else str(result["status"])
        
        if gstin not in vendor_map:
            vendor_map[gstin] = {
                "total_invoices": 0,
                "matched_count": 0,
                "missing_in_2b_count": 0,
                "risky_count": 0,
                "total_taxable_value": 0.0,
                "total_itc_amount": 0.0,
                "risky_itc_amount": 0.0
            }
        
        vendor_map[gstin]["total_invoices"] += 1
        vendor_map[gstin]["total_taxable_value"] += inv.taxable_value
        itc = inv.igst + inv.cgst + inv.sgst
        vendor_map[gstin]["total_itc_amount"] += itc
        
        if status_key == "MATCHED":
            vendor_map[gstin]["matched_count"] += 1
        elif status_key == "MISSING_IN_2B":
            vendor_map[gstin]["missing_in_2b_count"] += 1
        elif status_key == "RISKY_ITC":
            vendor_map[gstin]["risky_count"] += 1
            vendor_map[gstin]["risky_itc_amount"] += itc
    
    summaries = []
    for gstin, data in vendor_map.items():
        if data["risky_count"] > 0 or data["missing_in_2b_count"] > 0:
            risk_level = VendorRiskLevel.HIGH
        elif data["matched_count"] < data["total_invoices"]:
            risk_level = VendorRiskLevel.MEDIUM
        else:
            risk_level = VendorRiskLevel.LOW
        
        summaries.append(VendorRiskSummary(
            vendor_gstin=gstin,
            total_invoices=data["total_invoices"],
            matched_count=data["matched_count"],
            missing_in_2b_count=data["missing_in_2b_count"],
            risky_count=data["risky_count"],
            total_taxable_value=data["total_taxable_value"],
            total_itc_amount=data["total_itc_amount"],
            risky_itc_amount=data["risky_itc_amount"],
            vendor_risk_level=risk_level
        ))
    
    return sorted(summaries, key=lambda x: (x.vendor_risk_level.value, -x.risky_itc_amount))
