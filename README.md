# btp-mcp-server-python
Sample implementation of a MCP server on BTP in Python


MCP is the new standard for tool access for AI Agents. Developers in the SAP sphere build extensions and integrations on SAP BTP and nowadays building MCP servers is similarly relevant to expose functionalities to an Agent. In this blog post I am sharing a little sample MCP server written in Python to expose some functionality towards an agent. 

Drawio showing scenario

For the scenario we will build on top of SAP Cloud Foundry - a very flexible and low cost runtime option we have on BTP. There is certainly the possibility to build this on Kyma as well.
In this example I will build a research tool powered by the Perplexity API exposed on Generative AI Hub - because I want my Joule Studio based agents being able to query real-time data from the web. To secure the access to the MCP - I am using Cloud Identity Services - Identity Authentication (IAS) to implement a authentication check.

Note: You might as well wonder why not using the existing MCP directly from Perplexity? a) it's a nice tutorial exercise to build a Python wrapper - and b) the Generative AI Hub does expose the API - but not the API key. The MCP server directly from Perplexity basically requires me to hand in a key to make the requests on my behalf directly against their native API. This is not a scenario the Generative AI Hub supports - because we always need to proxy via that Generative AI Hub API with the Generative AI Hub credentials.


Let's directly have a look at how the code can look like for such a super simple example: In this case we utilize the popular fast_mcp library for the basic support of MCP's protocol specifications. This is indeed helpful and can get us started super easily. For the example we just expose a single tool with the decorator mcp.tool in which we execute any function.

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


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Now for BTP specific we need to do a few modifications. To ensure the fast_mcp server is running well and also registered as a healthy application - we need to run it on the specific Cloud Foundry provided port - that is accessible via the environment variable PORT. In addition we specify the "transport". In my case I want to use the HTTP transport.
To ensure the server is recongnized as a healty application we provide the health check health check http endpoint.

The mainfest for this MCP sample looks like this

---
applications:
- name: research-mcp-server-simple
  memory: 1024M
  disk_quota: 4024M
  buildpack: python_buildpack
  command: python server.py

So pretty straigt forward.

If we want to enable our service to provide a tool for perplexity - we can do so by modifying it the following way:

First we add the file perplexity.py to invoke the Generative AI Hub:

"""
Perplexity Research Tool via SAP Gen AI Hub

Simple interface to Perplexity AI with citation support.
"""

import json
import requests
import time
from typing import Dict


class PerplexityClient:
    """Client for Perplexity API via SAP Gen AI Hub native proxy."""

    def __init__(self, config_file: str = 'ai_core_key.json'):
        """Initialize the client with AI Core credentials."""
        self.config = self._load_config(config_file)
        self.token = None
        self.token_expiry = 0
        self._refresh_token()
        self.deployment_id = os.environ.get("AI_CORE_DEPLOYMENT_ID", "your-deployment-id")
        self.base_url = self.config['serviceurls']['AI_API_URL']
        self.api_url = f"{self.base_url}/v2/inference/deployments/{self.deployment_id}/chat/completions"

    def _load_config(self, config_file: str) -> Dict:
        """Load AI Core configuration from JSON file."""
        with open(config_file) as f:
            return json.load(f)

    def _get_access_token(self) -> str:
        """Get OAuth access token from AI Core."""
        token_response = requests.post(
            f"{self.config['url']}/oauth/token",
            auth=(self.config['clientid'], self.config['clientsecret']),
            data={'grant_type': 'client_credentials'},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        return token_response.json()['access_token']

    def _refresh_token(self) -> None:
        """Refresh the access token and set expiry time."""
        token_response = requests.post(
            f"{self.config['url']}/oauth/token",
            auth=(self.config['clientid'], self.config['clientsecret']),
            data={'grant_type': 'client_credentials'},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        token_data = token_response.json()
        self.token = token_data['access_token']
        # Set expiry time (default to 3600 seconds if not provided, subtract 60s buffer)
        expires_in = token_data.get('expires_in', 3600)
        self.token_expiry = time.time() + expires_in - 60

    def _ensure_valid_token(self) -> None:
        """Check if token is expired and refresh if needed."""
        if time.time() >= self.token_expiry:
            self._refresh_token()

    def research(self, query: str) -> str:
        """
        Research a query using Perplexity AI with real-time web search.

        Args:
            query: The research question

        Returns:
            Formatted response with answer and citations
        """
        # Ensure token is valid before making request
        self._ensure_valid_token()

        # Build payload
        payload = {
            "model": "sonar-pro",
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 5000,
            "temperature": 0.3,
            "search_context_size": "low",
            "return_citations": True,
            "return_related_questions": True
        }

        # Make request
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "AI-Resource-Group": "default"
        }

        response = requests.post(self.api_url, json=payload, headers=headers)

        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"

        result = response.json()

        # Extract data
        content = result['choices'][0]['message']['content'] if 'choices' in result else "No content"
        citations = result.get('citations', [])
        related = result.get('related_questions', [])

        # Format output
        output = [
            "=" * 80,
            f"QUERY: {query}",
            "=" * 80,
            "",
            content,
            ""
        ]

        if citations:
            output.extend([
                "=" * 80,
                f"SOURCES ({len(citations)} citations)",
                "=" * 80
            ])
            for i, url in enumerate(citations, 1):
                output.append(f"[{i}] {url}")
            output.append("")

        if related:
            output.extend([
                "=" * 80,
                "RELATED QUESTIONS",
                "=" * 80
            ])
            for q in related:
                output.append(f"  • {q}")

        return "\n".join(output)


In the code we use the service key to access the Generative AI Hub - call the native perplexity api to create a completion for the sonar model. It is a model that enriches its results with web search. Because of that we can format the output nicely to include the references as well. 

Note: I am not using the unified api from the orchestration module here - because we do not get the citations from that API yet.

with that in place our server py now looks like this:


from starlette.responses import JSONResponse
from fastmcp import FastMCP
import os
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


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


Basically we just invoke the Perplecity class to hand in the query of the user/agent.


Now lets add a bit of complexity by looking at how to secure such a MCP server written in Python:

The best option is to use the IAS service. In my previous blog I detailed out how to implement authentication checks in Python powered by the IAS service. Check this out for background information and specifically how to setup the configuration and client credentials on IAS side.

Preparation: There are a number of steps to setup the configuration on IAS side. Please refer to my other blog and complete all the steps in section "". You should end up with client credentials, a token service url.

For this case we modify our perplexity mcp server file to add a middleware:

from fastmcp import FastMCP
from fastapi import FastAPI, Request
import os
import requests
import jwt
import uvicorn
from perplexity import PerplexityClient
from fastapi.responses import JSONResponse
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

# Add health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

The main changes: We added a middleware that takes care of checking the token. This ensures that the MCP server can only be utilized by authenticated clients. claude to add some details on the code here ###

Note: Adding middleware in http servers is pretty straigt forward. For fast_mcp we need to host the mcp app via fast_

I recommend testing the setup locally and have therefore built a little test_mcp_client python script - that sends a few messages to the mcp server to validate wheter or not it is indeed authenticating and working in proper mcp manner.

See some results like this

## 1. Auth Rejection (without token)

curl "https://research-mcp-server-ias-auth.cfapps.sap.hana.ondemand.com/mcp"

Response: 401 - {"detail":"Missing token"}

## 2. Get Session (with token)

curl "https://research-mcp-server-ias-auth.cfapps.sap.hana.ondemand.com/mcp" \
  -H "Authorization: Bearer eyJqa3U..."

Response: 200 OK with mcp-session-id header

and indeed it works nicely.

Now that we have the complete MCP Server - lets have a look at how we can utilize it in Joule Studio to extend an Agent:

# Finally using the MCP Server from Joule Studio:

Lets quickly see how we can utilize this new MCP Server directly within Joule Studio to build a little Researcher Agent. It should be able to reseach any information for now. But the background idea for sure is- that we use that MCP server in conjunction with other tools and proper use-cases:

First we need to create a Destination for the MCP Server

This is done by Navigating to the BTP Subaccount Joule Studio is residing in and going to Connectivity > Destinations

In here we specify our URL Note: Not ending with /mcp - because this will be attached later.
And we can put in the client credentials

![Research MCP Add](images/research%20mcp%20add.png)

Create Agent image

In the Joule extension Project we can create an Agent and provide it its expertise, and prompting. Most importantly the section MCP is where we add the new Research MCP Server. Here we are prompted to select a Destination - we use our researcher destination. Optionally we can also change the mcp path. In this case /mcp is fine and going ahead we see the tools available on that MCP Server.

![Research Agent](images/research%20agent.png)

Now lets test it in action - started the agent and asked him to resarch the current situation in the middle east and it works! Uptodate information directly in Joule - can now be combined with any business transactional data one might pull from a S4 system.

![Researcher Result](images/researcher%20result.png)

By the way check out my blog on connecting Joule Studio to on-premises HTTP APIs.

In the Github I added all the different examples including the simple example, with auth based on IAS as well as based on XSUAA and the perplexity code. Hope you found this interesting. Leave a comment in case any doubts.