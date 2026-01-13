from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
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
        
        # Determine Action Type (Simple heuristic based on path)
        action_type = "UNKNOWN"
        if "upload" in endpoint:
            action_type = "UPLOAD"
        elif "reconcile" in endpoint:
            action_type = "RECONCILE"
        elif "explain" in endpoint:
            action_type = "EXPLAIN"
        elif "health" in endpoint:
            action_type = "HEALTH_CHECK"

        # 2. Capture & Hash Input
        input_hash = None
        request_body_bytes = b""
        try:
            # We must consume the stream carefully to allow downstream to read it again
            # Starlette/FastAPI request body is a stream. To read it here, we need to cache it.
            # NOTE: For large files, this is memory intensive. In a real system, we might limit this.
            request_body_bytes = await request.body()
            # Always hash the body, even if empty, for determinism
            input_hash = hashlib.sha256(request_body_bytes).hexdigest()
        except Exception:
            pass # Fail silently
            
        # Re-inject body for downstream
        async def receive():
            return {"type": "http.request", "body": request_body_bytes}
        request._receive = receive

        # 3. Process Request
        response = None
        status = AuditStatus.FAILURE
        output_hash = None
        
        try:
            response = await call_next(request)
            if 200 <= response.status_code < 300:
                status = AuditStatus.SUCCESS
            
            # 4. Capture & Hash Output
            # We need to peek at the response body. StreamingResponse makes this tricky.
            # We iterate the body, hash it, and reconstruct the response.
            response_body_bytes = b""
            async for chunk in response.body_iterator:
                response_body_bytes += chunk
            
            # Always hash response, even if empty
            output_hash = hashlib.sha256(response_body_bytes).hexdigest()
            
            # Reconstruct response to be sent back
            response = Response(
                content=response_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except Exception as e:
            # If application raised unhandled exception
            status = AuditStatus.FAILURE
            raise e
        finally:
            # 5. Log Event (Fail Silently)
            try:
                entry = AuditLogEntry(
                    endpoint=endpoint,
                    method=method,
                    action_type=action_type,
                    input_hash=input_hash,
                    output_hash=output_hash,
                    status=status
                )
                audit_repo.save(entry)
            except Exception as log_error:
                logger.error(f"Audit Logging Failed: {log_error}")

        return response
