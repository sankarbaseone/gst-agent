from openai import OpenAI, OpenAIError
import json
import logging
from app.schemas.explanation import ExplainRequest, ExplainResponse
from app.schemas.reconciliation import ReconciliationStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize client (assumes OPENAI_API_KEY env var is set)
# in production this should be handled more gracefully if key is missing
try:
    client = OpenAI()
except Exception:
    client = None
    logger.warning("OpenAI client could not be initialized. AI features will respond with fallback.")

SYSTEM_PROMPT = """
You are a pure, read-only reconciliation analyst for a GST compliance system.
Your goal is to explain the mismatch between a Customer Invoice and a Government GSTR-2B record based strictly on the provided data.

RULES:
1. DO NOT change the reconciliation status.
2. DO NOT perform new calculations or invent numbers.
3. DO NOT advise on tax filing compliance (legal advice).
4. IF there is no client, return "Needs human review".
5. Output valid JSON only.

OUTPUT FORMAT:
{
  "explanation": "Plain English explanation...",
  "root_cause": "Category (e.g., Data Entry Error, Timing Issue, Vendor Non-Compliance)",
  "suggested_action": "Action (e.g., Contact Vendor, Verify Date, Accept Mismatch)"
}
"""

def generate_explanation(request: ExplainRequest) -> ExplainResponse:
    # 1. Fallback if no client or dangerous input
    fallback_response = ExplainResponse(
        explanation="Automated explanation unavailable. Please review manually.",
        root_cause="System Limitation",
        suggested_action="Manual Review",
        original_status=request.status
    )

    if not client:
        return fallback_response

    # 2. Construct Prompt
    user_content = f"""
    Status: {request.status.value}
    Invoice: {request.invoice_number} (GSTIN: {request.gstin})
    Differences: {json.dumps(request.factual_diffs)}
    
    Explain this situation.
    """

    try:
        # 3. Call LLM
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # or gpt-4
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0, # Deterministic output
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # 4. Validate & Guardrail
        # Ensure we return the ORIGINAL status, completely ignoring anything AI might imply about status
        return ExplainResponse(
            explanation=data.get("explanation", "No explanation provided."),
            root_cause=data.get("root_cause", "Unknown"),
            suggested_action=data.get("suggested_action", "Review"),
            original_status=request.status
        )

    except (OpenAIError, json.JSONDecodeError, Exception) as e:
        logger.error(f"AI Generation Failed: {e}")
        return fallback_response
