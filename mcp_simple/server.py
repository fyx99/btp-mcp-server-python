from starlette.responses import JSONResponse
from fastmcp import FastMCP
import os

# Initialize FastMCP server
mcp = FastMCP("Simple Math Server")


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


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))