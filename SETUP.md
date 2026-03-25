# Setup Guide

This guide walks you through setting up and deploying the MCP servers to SAP BTP Cloud Foundry.

## Prerequisites

- SAP BTP account with Cloud Foundry environment
- Cloud Foundry CLI installed and logged in (`cf login`)
- Python 3.9+ installed locally (for local testing)
- SAP Generative AI Hub access with service key (for Perplexity examples)
- SAP Cloud Identity Services (IAS) tenant (for authentication example)

## Project Structure

```
btp-mcp-server-python/
├── mcp_simple/          # Basic MCP server example
├── mcp_perplexity/      # MCP server with Perplexity AI integration
├── mcp_ias_auth/        # Secured MCP server with IAS authentication
└── mcp_xsuaa_auth/      # MCP server with XSUAA authentication
```

## Quick Start

### 1. Simple MCP Server

The simplest example to get started:

```bash
cd mcp_simple
cf push
```

That's it! Your MCP server is now running on Cloud Foundry.

### 2. Perplexity Research Server

Requires AI Core configuration via environment variables:

**Step 1:** Create `.env` file:
```bash
cd mcp_perplexity
cp .env.example .env
```

**Step 2:** Fill in your AI Core credentials in `.env`:
```
AI_CORE_CLIENT_ID=your-ai-core-client-id
AI_CORE_CLIENT_SECRET=your-ai-core-client-secret
AI_CORE_AUTH_URL=https://your-tenant.authentication.sap.hana.ondemand.com
AI_CORE_API_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
AI_CORE_DEPLOYMENT_ID=your-deployment-id
```

Get these values from your AI Core service key in BTP Cockpit.

**Step 3:** Deploy:
```bash
cf push
```

### 3. Secured MCP Server (IAS Auth)

Adds authentication layer using IAS:

**Step 1:** Complete Perplexity setup (above)

**Step 2:** Configure both IAS and AI Core in `.env`:
```bash
cd mcp_ias_auth
cp .env.example .env
```

Edit `.env`:
```
# IAS Configuration
IAS_ISSUER=https://your-tenant.accounts.ondemand.com
IAS_AUDIENCE=your-ias-client-id

# AI Core Configuration
AI_CORE_CLIENT_ID=your-ai-core-client-id
AI_CORE_CLIENT_SECRET=your-ai-core-client-secret
AI_CORE_AUTH_URL=https://your-tenant.authentication.sap.hana.ondemand.com
AI_CORE_API_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
AI_CORE_DEPLOYMENT_ID=your-deployment-id
```

**Step 3:** Deploy:
```bash
cf push
```

**Step 4:** Test authentication:
```bash
# Should fail with 401
curl https://your-app.cfapps.sap.hana.ondemand.com/mcp

# Should succeed with valid token
curl https://your-app.cfapps.sap.hana.ondemand.com/mcp \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Local Development

### Running Locally

```bash
cd mcp_simple  # or any other module
pip install -r requirements.txt
python server.py
```

The server starts on `http://localhost:8080`

### Testing with Test Client

For the IAS auth example, use the included test client:

```bash
cd mcp_ias_auth
cp .env.example .env
# Edit .env and add the test client variables at the bottom
python test_client.py
```

## Configuration Files

### Environment Variables (.env)

All configuration is done via environment variables in a `.env` file. Each module has an `.env.example` template.

**AI Core Configuration:**
- `AI_CORE_CLIENT_ID`: Your AI Core client ID
- `AI_CORE_CLIENT_SECRET`: Your AI Core client secret
- `AI_CORE_AUTH_URL`: Authentication URL (e.g., `https://your-tenant.authentication.sap.hana.ondemand.com`)
- `AI_CORE_API_URL`: AI Core API URL (e.g., `https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com`)
- `AI_CORE_DEPLOYMENT_ID`: Your Perplexity deployment ID from AI Core

**IAS Configuration (for auth examples):**
- `IAS_ISSUER`: Your IAS tenant URL
- `IAS_AUDIENCE`: Your IAS application client ID

**Cloud Foundry:**
- `PORT`: Server port (auto-set by Cloud Foundry)

Get AI Core credentials from your AI Core service key in BTP Cockpit.

## Cloud Foundry Deployment

### Using manifest.yml

Each module includes a `manifest.yml`. Deploy with:

```bash
cf push
```

### Setting Environment Variables

Option 1 - Via manifest.yml:
```yaml
applications:
- name: my-mcp-server
  env:
    AI_CORE_CLIENT_ID: your-client-id
    AI_CORE_CLIENT_SECRET: your-client-secret
    AI_CORE_AUTH_URL: https://your-tenant.authentication.sap.hana.ondemand.com
    AI_CORE_API_URL: https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
    AI_CORE_DEPLOYMENT_ID: your-deployment-id
    IAS_ISSUER: https://your-tenant.accounts.ondemand.com
    IAS_AUDIENCE: your-ias-client-id
```

Option 2 - Via CF CLI:
```bash
cf set-env my-mcp-server AI_CORE_CLIENT_ID "your-client-id"
cf set-env my-mcp-server AI_CORE_CLIENT_SECRET "your-client-secret"
cf set-env my-mcp-server AI_CORE_DEPLOYMENT_ID "your-deployment-id"
cf restage my-mcp-server
```

## Integrating with Joule Studio

### Step 1: Create Destination

In BTP Cockpit → Connectivity → Destinations:

- **Name**: `research-mcp-server`
- **Type**: `HTTP`
- **URL**: `https://your-app.cfapps.sap.hana.ondemand.com` (without `/mcp`)
- **Authentication**: `OAuth2ClientCredentials` (for IAS auth version)
  - Client ID: Your IAS client ID
  - Client Secret: Your IAS client secret
  - Token Service URL: `https://your-tenant.accounts.ondemand.com/oauth2/token`

### Step 2: Add to Joule Studio Agent

1. Create new Agent in Joule Extension Project
2. Go to **MCP** section
3. Click **Add MCP Server**
4. Select your destination
5. Verify path is `/mcp`
6. Save - you'll see available tools

## Troubleshooting

### App crashes on CF
- Check logs: `cf logs my-app --recent`
- Verify all required environment variables are set
- Check `.env` file exists locally (for local testing)

### Authentication fails
- Verify IAS configuration in environment variables
- Check token expiry
- Ensure correct issuer and audience

### Deployment not found
- Verify `AI_CORE_DEPLOYMENT_ID` matches your AI Core instance
- Ensure deployment is active

### Missing environment variables
- Ensure `.env` file is created from `.env.example`
- For CF deployments, check `cf env my-app`

## Next Steps

- Read the full [blog post](BLOG_POST.md) for detailed explanations
- Check out the [README](README.md) for architecture overview
- Explore the code in each module

## Getting Help

- Open an issue on GitHub
- Check SAP Community for BTP questions
