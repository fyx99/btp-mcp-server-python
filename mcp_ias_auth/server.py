import os
import jwt
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from perplexity import PerplexityClient
from starlette.middleware.base import BaseHTTPMiddleware

# Initialize Perplexity client
client = PerplexityClient()

# Create MCP server
mcp = FastMCP("Research Server")

# Config - Load from environment variables
ISSUER = os.environ.get("IAS_ISSUER", "https://your-tenant.accounts.ondemand.com")
JWKS_URL = f"{ISSUER}/oauth2/certs"
AUDIENCE = os.environ.get("IAS_AUDIENCE", "your-client-id-here")

class IASAuthMiddleware(BaseHTTPMiddleware):

    def get_public_key(self, token: str):
        """Holt JWKS und findet den passenden Public Key"""
        kid = jwt.get_unverified_header(token)["kid"]
        jwks = requests.get(JWKS_URL).json()

        for key in jwks["keys"]:
            if key["kid"] == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(key)

        raise Exception("No matching key found")

    def verify_token(self, token: str):
        """Validiert JWT Token"""
        public_key = self.get_public_key(token)
        payload = jwt.decode(token, public_key, algorithms=["RS256"],
                            audience=AUDIENCE, issuer=ISSUER)

        if "api_read_access" not in payload.get("ias_apis", []):
            raise Exception("Missing required ias_apis scope")

        return payload
    
    async def dispatch(self, request: Request, call_next):
        # Check if authorization header exists
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing token"})

        token = auth_header.split(" ")[1]

        try:
            payload = self.verify_token(token)
            request.state.user = payload
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": str(e)})

        return await call_next(request)


@mcp.tool()
def research(query: str) -> str:
    """
    Research tool using Perplexity AI with real-time web search and citations.

    Args:
        query: The research query (simple string input)

    Returns:
        Research results with answer and source citations
    """
    return client.research(query)

# Create ASGI app from MCP server
mcp_app = mcp.http_app(path='/mcp')

# Key: Pass lifespan to FastAPI
app = FastAPI(title="Researcher MCP", lifespan=mcp_app.lifespan)

# Add IAS authentication middleware
mcp_app.add_middleware(IASAuthMiddleware)

# Mount the MCP server
app.mount("/", mcp_app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

