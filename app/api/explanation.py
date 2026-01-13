from fastapi import APIRouter, HTTPException, Body
from app.schemas.explanation import ExplainRequest, ExplainResponse
from app.core.ai import generate_explanation

router = APIRouter()

@router.post("/explain-mismatch", response_model=ExplainResponse)
async def explain_mismatch(request: ExplainRequest = Body(...)):
    """
    Generate an AI-powered explanation for a reconciliation mismatch.
    This is a read-only operation and does not alter the invoice status.
    """
    # Guardrail: If status is MATCHED, explanation might be redundant but strictly allowed if requested.
    # We pass strictly factual data to the engine.
    
    response = generate_explanation(request)
    return response
