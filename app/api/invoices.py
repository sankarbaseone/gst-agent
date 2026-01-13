from fastapi import APIRouter, File, UploadFile, HTTPException, Header, Response
from typing import List, Optional
import csv
import io
import logging
from app.schemas.invoice import Invoice
from pydantic import ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
PLAN_LIMITS = {
    "BASIC": 100,
    "PRO": 500,
    "ENTERPRISE": 1000
}

INVOICE_STORE = [] # Replace with DB later

@router.post("/invoices/upload")
async def upload_invoices(
    file: UploadFile = File(...),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_plan: str = Header("BASIC", alias="X-Plan")
):
    # 1. Validate Plan
    if x_plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid plan '{x_plan}'. Allowed: BASIC, PRO, ENTERPRISE")
    
    limit = PLAN_LIMITS[x_plan]

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Only CSV files are accepted.")

    content = await file.read()
    
    try:
        decoded_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a valid UTF-8 CSV.")

    # 2. Parse & Validate Usage Limits
    try:
        csv_file = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(csv_file)
        
        # Check empty file or just headers
        # We need to list(rows) to count them, but be careful with memory if file is huge. 
        # Limits are small (1000 max), so list() is safe.
        rows = list(csv_reader)
        
        # Enforce Limit
        if len(rows) > limit:
             raise HTTPException(
                 status_code=413, 
                 detail=f"Invoice limit exceeded for your current plan ({x_plan}). Limit: {limit}, Uploaded: {len(rows)}"
             )

        # Validate Headers
        required_headers = {'gstin', 'invoice_no', 'invoice_date', 'taxable_value', 'cgst', 'sgst', 'igst'}
        if not csv_reader.fieldnames or not required_headers.issubset(set(csv_reader.fieldnames)):
            missing = required_headers - set(csv_reader.fieldnames or [])
            raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

        parsed_invoices: List[Invoice] = []
        
        for index, row in enumerate(rows):
            # Trim whitespace
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            
            try:
                invoice = Invoice(**clean_row)
                parsed_invoices.append(invoice)
            except ValidationError as e:
                # Format friendly message
                # e.errors() returns list of dicts
                error_msgs = []
                for err in e.errors():
                    loc = err.get("loc", ["unknown"])[0] 
                    msg = err.get("msg", "Invalid value")
                    error_msgs.append(f"{loc}: {msg}")
                
                raise ValueError(f"Row {index + 2}: {'; '.join(error_msgs)}") # +2 for header and 0-index

    except csv.Error:
        raise HTTPException(status_code=400, detail="Invalid CSV format.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # 3. Store (Simulated Isolation)
    # in real DB we would store tenant_id with invoice. 
    # For in-memory, we just append. Isolation is enforced at ingress (middleware).
    INVOICE_STORE.extend(parsed_invoices)
    
    logger.info(f"Processed {len(parsed_invoices)} invoices for tenant {x_tenant_id}")

    return {
        "status": "success",
        "total_invoices": len(parsed_invoices),
        "normalized_invoices": parsed_invoices
    }
