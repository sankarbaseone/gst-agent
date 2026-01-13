from fastapi import APIRouter, File, UploadFile, HTTPException, Header, Response
from typing import List, Optional, Dict, Any
import csv
import io
import logging
from datetime import datetime
from app.schemas.invoice import Invoice
from app.db.memory import APP_STATE
from app.core.reconciliation import reconcile_invoice
from pydantic import ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
PLAN_LIMITS = {
    "BASIC": 100,
    "PRO": 500,
    "ENTERPRISE": 1000
}

@router.post("/invoices/upload")
async def upload_invoices(
    file: UploadFile = File(...),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_plan: str = Header("BASIC", alias="X-Plan")
):
    if x_plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid plan '{x_plan}'")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format.")

    content = await file.read()
    try:
        decoded_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid encoding.")

    try:
        csv_file = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(csv_file)
        rows = list(csv_reader)
        
        if len(rows) > PLAN_LIMITS[x_plan]:
            raise HTTPException(status_code=413, detail=f"Limit exceeded for {x_plan}")

        parsed_invoices: List[Invoice] = []
        results: List[Dict[str, Any]] = []

        for index, row in enumerate(rows):
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            try:
                inv = Invoice(**clean_row)
                parsed_invoices.append(inv)
                
                # Use AUTHORITATIVE RECONCILIATION ENGINE
                result = reconcile_invoice(inv, index)
                results.append(result)

            except ValidationError:
                raise ValueError(f"Row {index + 2}: Invalid data")

        # Update authoritative central store
        APP_STATE[x_tenant_id] = {
            "invoices": parsed_invoices,
            "reconciliation": results,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Reconciliation COMPLETED for tenant: {x_tenant_id}. Count: {len(parsed_invoices)}")

        vendor_summary_results = []
        if x_plan in ["PRO", "ENTERPRISE"]:
            from app.core.vendor_aggregation import aggregate_vendor_risk
            vendor_summary = aggregate_vendor_risk(parsed_invoices, results)
            vendor_summary_results = [v.dict() for v in vendor_summary]
            APP_STATE[x_tenant_id]["vendor_summary"] = vendor_summary_results

        return {
            "status": "success",
            "total_invoices": len(parsed_invoices),
            "reconciliation_results": results,
            "vendor_summary": vendor_summary_results
        }

    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))
