import os
from starlette.responses import JSONResponse
from fastmcp import FastMCP
from perplexity import PerplexityClient

# Initialize FastMCP server
mcp = FastMCP("Research Server")

# Initialize Perplexity client
client = PerplexityClient()


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


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))