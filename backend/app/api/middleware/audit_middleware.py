"""
Middleware layer for Protocol Amendment Dependency Graph Engine.

Provides:
- Request/Response logging for audit trails
- Timing metrics for performance monitoring
- Error handling and correlation IDs
- Authentication validation
"""

import uuid
import time
import logging
from typing import Callable, Optional

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all incoming requests and outgoing responses for audit purposes.
    
    Captures:
    - Request ID (for traceability)
    - HTTP method and path
    - Request duration
    - Response status code
    - User identity (if authenticated)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract user info if available
        user_id = "anonymous"
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "sub", "unknown")
        
        # Log request
        start_time = time.time()
        logger.info(
            f"[AUDIT] Request Start | ID: {request_id} | "
            f"Method: {request.method} | Path: {request.url.path} | "
            f"User: {user_id}"
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Log response
            logger.info(
                f"[AUDIT] Request End | ID: {request_id} | "
                f"Status: {response.status_code} | Duration: {duration_ms:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[AUDIT] Request Failed | ID: {request_id} | "
                f"Error: {str(e)} | Duration: {duration_ms:.2f}ms",
                exc_info=True
            )
            raise


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has a correlation ID for distributed tracing.
    
    Uses existing X-Correlation-ID header if present,
    otherwise generates a new one.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for existing correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler that formats errors consistently.
    
    Provides:
    - Structured error responses
    - Error logging with context
    - Hides internal details from clients
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.error(
                f"[ERROR] Unhandled Exception | Request ID: {request_id} | "
                f"Path: {request.url.path} | Error: {str(e)}",
                exc_info=True
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred. Please contact support.",
                    "request_id": request_id,
                    "detail": str(e) if request.app.debug else None
                }
            )


class AuditTrailMiddleware(BaseHTTPMiddleware):
    """
    Specialized middleware for capturing audit-relevant events.
    
    Tracks:
    - Data modifications (POST, PUT, DELETE)
    - Access to sensitive endpoints
    - Authentication events
    """
    
    SENSITIVE_PATHS = [
        "/api/v1/amendments",
        "/api/v1/impact",
        "/api/v1/review",
        "/api/v1/audit",
    ]
    
    WRITE_METHODS = ["POST", "PUT", "DELETE", "PATCH"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is an audit-relevant request
        is_sensitive = any(
            request.url.path.startswith(path) 
            for path in self.SENSITIVE_PATHS
        )
        is_write = request.method in self.WRITE_METHODS
        
        # Capture request body for write operations
        request_body = None
        if is_write and is_sensitive:
            try:
                request_body = await request.body()
                # Restore body for downstream processing
                request._body = request_body
            except Exception:
                pass
        
        # Get user info
        user_id = "anonymous"
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "sub", "unknown")
        
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log audit event for sensitive operations
        if is_sensitive:
            audit_event = {
                "event_type": "api_access",
                "request_id": getattr(request.state, "request_id", "unknown"),
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "timestamp": time.time(),
            }
            
            if is_write:
                audit_event["operation_type"] = "write"
                logger.info(f"[AUDIT-WRITE] {audit_event}")
            else:
                audit_event["operation_type"] = "read"
                logger.info(f"[AUDIT-READ] {audit_event}")
        
        return response


def setup_middleware(app):
    """
    Configure all middleware for the FastAPI application.
    
    Order matters:
    1. CorrelationID - First to ensure ID is available
    2. ErrorHandler - Catch errors early
    3. RequestLogging - Log all requests
    4. AuditTrail - Specialized audit logging
    """
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuditTrailMiddleware)
    
    logger.info("Middleware stack initialized successfully")
