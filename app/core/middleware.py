from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.concurrency import iterate_in_threadpool
import hashlib
import json
from app.core.audit import audit_repo
from app.schemas.audit import AuditLogEntry, AuditStatus
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # 1. Capture Request Details
        endpoint = request.url.path
        method = request.method
        
        # Determine Action Type
        action_type = "UNKNOWN"
        if "upload" in endpoint:
            action_type = "UPLOAD"
        elif "reconcile" in endpoint:
            action_type = "RECONCILE"
        elif "explain" in endpoint:
            action_type = "EXPLAIN"
        elif "health" in endpoint:
            action_type = "HEALTH_CHECK"

        # 2. Strict Tenant ID Check
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # If missing, we must reject, unless it's a health check? 
        # Requirement: "Middleware must reject any request missing X-Tenant-ID with HTTP 400"
        # "No business logic should execute without tenant_id"
        # We will allow health check to pass or require it there too?
        # Usually health check is public. But the requirement is strict: "Middleware must reject ANY request"
        # Let's apply it generally, assuming /health is an API endpoint. 
        # Actually, verifying readiness usually implies system level. 
        # But for compliance SaaS, maybe even health is protected? 
        # Let's stick to the prompt: "Middleware must reject ANY request missing X-Tenant-ID"
        # We will use "MISSING" for the log entry if we reject.

        if not tenant_id:
             # If strictly enforcing, we return 400 immediately.
             # We still want to audit this failure.
             tenant_id_for_log = "MISSING"
             status = AuditStatus.FAILURE
             
             # We assume empty body hash for rejection if we don't read it
             # But let's follow the standard flow: read body (to hash), then reject.
             # Or just reject to save bandwidth. 
             # Let's reject immediately. Input hash will be None or empty hash.
             
             # We need to construct the 400 response
             response = JSONResponse(
                 status_code=400, 
                 content={"detail": "Missing tenant identifier"}
             )
             
             # Log the rejection
             try:
                entry = AuditLogEntry(
                    endpoint=endpoint,
                    method=method,
                    action_type=action_type,
                    tenant_id=tenant_id_for_log,
                    input_hash=None, # Did not read body
                    output_hash=None, # Standard error response, maybe not worth hashing? Or hash the JSON?
                    status=status
                )
                audit_repo.save(entry)
             except Exception as e:
                 logger.error(f"Audit Logging Failed: {e}")
                 
             return response

        # 3. Capture & Hash Input
        input_hash = None
        request_body_bytes = b""
        try:
            request_body_bytes = await request.body()
            # Always hash the body, even if empty, for determinism
            input_hash = hashlib.sha256(request_body_bytes).hexdigest()
        except Exception:
            pass # Fail silently
            
        # Re-inject body
        async def receive():
            return {"type": "http.request", "body": request_body_bytes}
        request._receive = receive

        # 4. Process Request
        response = None
        status = AuditStatus.FAILURE
        output_hash = None
        
        try:
            response = await call_next(request)
            if 200 <= response.status_code < 300:
                status = AuditStatus.SUCCESS
            
            # 5. Capture & Hash Output
            response_body_bytes = b""
            async for chunk in response.body_iterator:
                response_body_bytes += chunk
            
            # Always hash response
            output_hash = hashlib.sha256(response_body_bytes).hexdigest()
            
            # Reconstruct response
            response = Response(
                content=response_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except Exception as e:
            status = AuditStatus.FAILURE
            raise e
        finally:
            # 6. Log Event
            try:
                entry = AuditLogEntry(
                    endpoint=endpoint,
                    method=method,
                    action_type=action_type,
                    tenant_id=tenant_id,
                    input_hash=input_hash,
                    output_hash=output_hash,
                    status=status
                )
                audit_repo.save(entry)
            except Exception as log_error:
                logger.error(f"Audit Logging Failed: {log_error}")

        return response
