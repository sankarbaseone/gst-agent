from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Plan Limits for UI
PLAN_LIMITS = {
    "BASIC": 100,
    "PRO": 500,
    "ENTERPRISE": 1000
}

@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@router.get("/onboarding/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})

@router.post("/onboarding/setup")
async def setup_session(
    request: Request,
    business_name: str = Form(...),
    gstin: str = Form(...),
    email: str = Form(...)
):
    # Generate Server-Side Tenant ID
    tenant_id = str(uuid.uuid4())
    
    # Store in HttpOnly Cookie => Redirect to Plan
    response = RedirectResponse(url="/onboarding/plan", status_code=303)
    response.set_cookie(key="gst_tenant_id", value=tenant_id, httponly=True, path="/")
    
    # Dummy session log (in real app, act on business_name etc)
    return response

@router.get("/onboarding/plan", response_class=HTMLResponse)
async def select_plan_page(request: Request):
    return templates.TemplateResponse("plan.html", {"request": request})

@router.post("/onboarding/plan")
async def save_plan(request: Request, plan: str = Form(...)):
    if plan not in PLAN_LIMITS:
        plan = "BASIC"
        
    response = RedirectResponse(url="/app", status_code=303)
    response.set_cookie(key="gst_plan", value=plan, httponly=True, path="/")
    return response

@router.get("/app", response_class=HTMLResponse)
async def app_page(request: Request):
    # Strict Tenant Session Check
    tenant_id = request.cookies.get("gst_tenant_id")
    plan = request.cookies.get("gst_plan")
    
    if not tenant_id:
        return RedirectResponse(url="/")
        
    if not plan:
        plan = "BASIC"
    
    limit = PLAN_LIMITS.get(plan, 100)

    # Render App with injected context for JS to use in headers
    # "Client-side JS must NEVER generate or modify tenant_id" -> Consuming strictly from server injection is safe.
    return templates.TemplateResponse("app.html", {
        "request": request,
        "tenant_id": tenant_id,
        "plan": plan,
        "limit": limit
    })
