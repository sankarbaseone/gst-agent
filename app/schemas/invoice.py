from pydantic import BaseModel, Field, field_validator, ValidationInfo
from datetime import date, datetime
import re
from typing import Optional

class Invoice(BaseModel):
    gstin: str
    invoice_number: str = Field(..., validation_alias="invoice_no")
    invoice_date: date
    taxable_value: float
    cgst: float
    sgst: float
    igst: float
    source: str = "customer"

    @field_validator('gstin')
    @classmethod
    def validate_gstin(cls, v):
        pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        if not re.match(pattern, v):
            raise ValueError('Invalid GSTIN format')
        return v
    
    @field_validator('invoice_date', mode='before')
    @classmethod
    def validate_date_format(cls, v):
        # Ensure input is string and formatted strict YYYY-MM-DD before parsing
        if isinstance(v, str):
            try:
                # strict parsing
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator('taxable_value', 'cgst', 'sgst', 'igst', mode='before')
    @classmethod
    def validate_numeric(cls, v, info: ValidationInfo):
        # Strict numeric check for CSV strings
        if isinstance(v, str):
            if not re.match(r'^-?\d+(\.\d+)?$', v.strip()):
                 raise ValueError(f"{info.field_name} must be strictly numeric")
        return v

