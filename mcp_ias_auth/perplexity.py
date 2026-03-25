"""
Perplexity Research Tool via SAP Gen AI Hub

Simple interface to Perplexity AI with citation support.
"""

import json
import os
import requests
import time
from typing import Dict


class PerplexityClient:
    """Client for Perplexity API via SAP Gen AI Hub native proxy."""

    def __init__(self):
        """Initialize the client with AI Core credentials from environment."""
        # Load from environment variables
        self.client_id = os.environ.get("AI_CORE_CLIENT_ID")
        self.client_secret = os.environ.get("AI_CORE_CLIENT_SECRET")
        self.auth_url = os.environ.get("AI_CORE_AUTH_URL")
        self.api_url_base = os.environ.get("AI_CORE_API_URL")
        self.deployment_id = os.environ.get("AI_CORE_DEPLOYMENT_ID", "your-deployment-id")

        # Validate required config
        if not all([self.client_id, self.client_secret, self.auth_url, self.api_url_base]):
            raise ValueError("Missing required AI Core environment variables. Check .env file.")

        self.token = None
        self.token_expiry = 0
        self._refresh_token()
        self.api_url = f"{self.api_url_base}/v2/inference/deployments/{self.deployment_id}/chat/completions"

    def _get_access_token(self) -> str:
        """Get OAuth access token from AI Core."""
        token_response = requests.post(
            f"{self.auth_url}/oauth/token",
            auth=(self.client_id, self.client_secret),
            data={'grant_type': 'client_credentials'},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        return token_response.json()['access_token']

    def _refresh_token(self) -> None:
        """Refresh the access token and set expiry time."""
        token_response = requests.post(
            f"{self.auth_url}/oauth/token",
            auth=(self.client_id, self.client_secret),
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
