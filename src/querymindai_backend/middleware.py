import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates/extracts a unique Request ID for every incoming request,
    stores it in the request state, and appends it to the outgoing response headers.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Retrieve or generate unique request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        # 3. Store in request state
        request.state.request_id = request_id
        
        # Call the next handler in the chain
        response = await call_next(request)
        
        # 2. Add request ID to the outgoing response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
