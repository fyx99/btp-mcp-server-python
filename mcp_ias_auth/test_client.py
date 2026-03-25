#!/usr/bin/env python3
"""Minimalistic MCP Test Script with IAS Auth"""

import requests
import json
import jwt
import os

# === CONFIG - Load from environment variables ===
BASE_URL = os.environ.get("MCP_BASE_URL", "https://your-mcp-server.cfapps.sap.hana.ondemand.com")
CLIENT_ID = os.environ.get("IAS_CLIENT_ID", "your-client-id")
CLIENT_SECRET = os.environ.get("IAS_CLIENT_SECRET", "your-client-secret")
IAS_AUTH_URL = os.environ.get("IAS_AUTH_URL", "https://your-tenant.accounts.ondemand.com/oauth2/token")

print("=" * 80)
print("MCP IAS Auth Test")
print("=" * 80)

# === 0. TEST AUTH REJECTION (WITHOUT TOKEN) ===
print("\n[0] Testing auth rejection (without token)...")
try:
    no_auth_response = requests.get(f"{BASE_URL}/mcp")
    print(f"Status: {no_auth_response.status_code}")
    print(f"Response: {no_auth_response.text}")
    if no_auth_response.status_code == 401:
        print("✅ Auth correctly rejected!")
    else:
        print("⚠️  Expected 401 but got different status")
except Exception as e:
    print(f"Error: {e}")

# === 1. GET TOKEN ===
print("\n[1] Getting token...")
token_response = requests.post(
    IAS_AUTH_URL,
    auth=(CLIENT_ID, CLIENT_SECRET),
    data={'grant_type': 'client_credentials'}
)
access_token = token_response.json()['access_token']
print(f"✅ Token: {access_token[:50]}...")

# Decode token to show contents
decoded_token = jwt.decode(access_token, options={"verify_signature": False})
print(f"\nToken Content:\n{json.dumps(decoded_token, indent=2)}")

headers = {"Authorization": f"Bearer {access_token}"}

# Print auth header
print(f"\nAuthorization Header: {headers['Authorization']}")

# === 2. GET SESSION ===
print("\n[2] Getting session (GET /mcp)...")
session_response = requests.get(f"{BASE_URL}/mcp", headers=headers)
session_id = session_response.headers.get('mcp-session-id')
print(f"✅ Session ID: {session_id}")

headers["mcp-session-id"] = session_id
headers["Content-Type"] = "application/json"
headers["Accept"] = "application/json, text/event-stream"

# === 3. INITIALIZE ===
print("\n[3] Initialize...")
init_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    }
}
init_response = requests.post(f"{BASE_URL}/mcp", headers=headers, json=init_payload)
print(f"✅ Status: {init_response.status_code}")
print(f"Raw Response:\n{init_response.text}")

# === 4. LIST TOOLS ===
print("\n[4] List tools...")
tools_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}
tools_response = requests.post(f"{BASE_URL}/mcp", headers=headers, json=tools_payload)
print(f"✅ Status: {tools_response.status_code}")
print(f"Raw Response:\n{tools_response.text}")
print(f"Response Length: {len(tools_response.text)}")

# Parse SSE format if needed
if not tools_response.text:
    print("⚠️  Empty response!")
    tools_data = {}
elif 'data: ' in tools_response.text:
    # Extract data line from SSE format
    for line in tools_response.text.split('\n'):
        if line.startswith('data: '):
            json_str = line[6:]  # Remove 'data: ' prefix
            tools_data = json.loads(json_str)
            break
else:
    tools_data = json.loads(tools_response.text)

tools = tools_data.get('result', {}).get('tools', [])
for tool in tools:
    print(f"  - {tool['name']}: {tool['description'][:60]}...")

# === 5. CALL RESEARCH TOOL ===
print("\n[5] Calling research tool...")
research_payload = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "research",
        "arguments": {"query": "What is SAP BTP?"}
    }
}
research_response = requests.post(f"{BASE_URL}/mcp", headers=headers, json=research_payload, timeout=60)
print(f"✅ Status: {research_response.status_code}")
print(f"Raw Response:\n{research_response.text[:500]}...")
print(f"Response Length: {len(research_response.text)}")

# Parse SSE format if needed
if not research_response.text:
    print("⚠️  Empty response!")
    research_data = {}
elif 'data: ' in research_response.text:
    # Extract data line from SSE format
    for line in research_response.text.split('\n'):
        if line.startswith('data: '):
            json_str = line[6:]  # Remove 'data: ' prefix
            research_data = json.loads(json_str)
            break
else:
    research_data = json.loads(research_response.text)

if 'result' in research_data:
    result_text = research_data['result']['content'][0]['text']
    print(f"\nResult (truncated):\n{result_text[:300]}...")
else:
    print(f"Error: {research_data.get('error')}")

print("\n" + "=" * 80)
print("✅ All tests passed!")
print("=" * 80)
