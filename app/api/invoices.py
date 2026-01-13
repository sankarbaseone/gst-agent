from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
import csv
import io
import logging
from pydantic import ValidationError
from app.schemas.invoice import Invoice

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage placeholder
INVOICE_STORE: List[Invoice] = []

@router.post("/invoices/upload")
async def upload_invoices(file: UploadFile = File(...)):
    logger.info(f"Received file upload: {file.filename}")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Only CSV files are accepted.")

    content = await file.read()
    try:
        decoded_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a valid UTF-8 CSV.")

    csv_reader = csv.DictReader(io.StringIO(decoded_content))
    
    # Validate headers
    required_headers = {'gstin', 'invoice_no', 'invoice_date', 'taxable_value', 'cgst', 'sgst', 'igst'}
    if not csv_reader.fieldnames or not required_headers.issubset(set(csv_reader.fieldnames)):
        missing = required_headers - set(csv_reader.fieldnames or [])
        detail = f"Missing required columns: {', '.join(missing)}"
        logger.error(detail)
        raise HTTPException(status_code=400, detail=detail)

    parsed_invoices: List[Invoice] = []
    
    # Process rows
    rows = list(csv_reader) # Read all to memory to ensure atomicity/determinism
    logger.info(f"Processing {len(rows)} rows from CSV.")
    
    for index, row in enumerate(rows):
        # Trim whitespace from keys and values
        clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
        
        try:
            # Pydantic validation
            invoice = Invoice(**clean_row)
            parsed_invoices.append(invoice)
        except (ValueError, ValidationError) as e:
            # Basic validation error formatting
            # Extract meaningful message from ValidationError if possible
            error_msg = str(e)
            if isinstance(e, ValidationError):
                # errors() return list of dicts, simplified for readability
                error_msg = "; ".join([f"{err['loc'][-1]}: {err['msg']}" for err in e.errors()])
            
            detail = f"Row {index + 1} validation error: {error_msg}"
            logger.warning(detail)
            raise HTTPException(
                status_code=400, 
                detail=detail
            )

    # explicit assertions for verification
    assert len(parsed_invoices) == len(rows), "Mismatch between processed rows and parsed invoices"

    # Store normalized data
    INVOICE_STORE.extend(parsed_invoices)
    
    logger.info(f"Successfully normalized and stored {len(parsed_invoices)} invoices. Total store size: {len(INVOICE_STORE)}")

    return {
        "status": "success",
        "total_invoices": len(INVOICE_STORE),
        "normalized_invoices": parsed_invoices
    }
