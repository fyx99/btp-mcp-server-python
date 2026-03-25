from fastmcp import FastMCP
from fastapi import FastAPI
import os
import uvicorn
from auth_middleware import XSUAAAuthMiddleware

# Create MCP server
mcp = FastMCP("Math Server")

@mcp.tool()
def add(a: float, b: float) -> float:
    """
    Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b

# Create ASGI app from MCP server
mcp_app = mcp.http_app(path='/mcp')

# Key: Pass lifespan to FastAPI
app = FastAPI(title="Math MCP", lifespan=mcp_app.lifespan)

# Add XSUAA authentication middleware
mcp_app.add_middleware(XSUAAAuthMiddleware)

# Mount the MCP server
app.mount("/", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


