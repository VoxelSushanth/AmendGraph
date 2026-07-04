"""
Middleware package for Protocol Amendment Dependency Graph Engine.

Provides audit logging, error handling, correlation IDs, and request tracing.
"""

from .audit_middleware import (
    RequestLoggingMiddleware,
    CorrelationIDMiddleware,
    ErrorHandlerMiddleware,
    AuditTrailMiddleware,
    setup_middleware,
)

__all__ = [
    "RequestLoggingMiddleware",
    "CorrelationIDMiddleware",
    "ErrorHandlerMiddleware",
    "AuditTrailMiddleware",
    "setup_middleware",
]