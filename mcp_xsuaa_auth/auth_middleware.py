"""
XSUAA Authentication Middleware for FastAPI
"""
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cfenv import AppEnv
import jwt
from sap import xssec



class XSUAAAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, dev_mode: bool = False):
        super().__init__(app)

        # Load environment and UAA service 
        try:
            env = AppEnv()
            self.uaa_service = env.get_service(name='xsuaa_mcp').credentials
            print("[AUTH] XSUAA authentication enabled")
        except Exception as e:
            print(f"[AUTH] Warning: Could not load XSUAA service: {e}")


    async def dispatch(self, request: Request, call_next):
        # Check if authorization header exists
        if 'authorization' not in request.headers:
            return JSONResponse(
                status_code=403,
                content={"error": "Missing authorization header"}
            )

        # Extract access token
        auth_header = request.headers.get('authorization')
        if not auth_header.startswith('Bearer '):
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid authorization header format"}
            )

        access_token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Decode and print token (without verification)
            print(jwt.decode(access_token, options={"verify_signature": False}))

            # Create security context and check scope
            security_context = xssec.create_security_context(access_token, self.uaa_service)

            # Check for the MCP access scope
            isAuthorized = security_context.check_scope('uaa.resource')

            print(f"Is Authorized: {isAuthorized}")
            print(f"Security Context: {security_context}")

            if not isAuthorized:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Unauthorized: Missing required scope 'uaa.resource'"}
                )

            # If authorized, proceed with request
            response = await call_next(request)
            return response

        except Exception as e:
            print(f"Auth error: {e}")
            return JSONResponse(
                status_code=403,
                content={"error": f"Authentication failed: {str(e)}"}
            )
