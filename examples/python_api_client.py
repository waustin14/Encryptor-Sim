#!/usr/bin/env python3
"""Encryptor Simulator API client example.

Demonstrates JWT authentication, token refresh, and protected endpoint access.

Usage:
    python python_api_client.py --host 192.168.1.100

Requirements:
    pip install requests
"""

import argparse
import sys
import time
from typing import Optional

import requests
import urllib3

# Suppress InsecureRequestWarning for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EncryptorSimClient:
    """API client for Encryptor Simulator automation."""

    def __init__(
        self, base_url: str, username: str, password: str, verify_ssl: bool = False
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: float = 0.0

    def login(self) -> None:
        """Authenticate and store JWT tokens."""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": self.username, "password": self.password},
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        data = response.json()["data"]
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        # Note: Hardcoded 3500s (58min) to refresh before 1-hour expiry.
        # Production code should decode JWT and read 'exp' claim instead.
        self.token_expires_at = time.time() + 3500
        print(f"Authenticated as {self.username}")

    def refresh_access_token(self) -> None:
        """Get a new access token using the refresh token."""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/refresh",
            json={"refreshToken": self.refresh_token},
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        data = response.json()["data"]
        self.access_token = data["accessToken"]
        # Note: Hardcoded expiry; production should decode JWT 'exp' claim
        self.token_expires_at = time.time() + 3500
        print("Access token refreshed")

    def _ensure_valid_token(self) -> None:
        """Refresh the access token if it has expired."""
        if not self.access_token or time.time() >= self.token_expires_at:
            if self.refresh_token:
                try:
                    self.refresh_access_token()
                    return
                except requests.HTTPError:
                    pass
            self.login()

    def _headers(self) -> dict:
        """Return Authorization headers."""
        self._ensure_valid_token()
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_me(self) -> dict:
        """Get current user profile."""
        response = requests.get(
            f"{self.base_url}/api/v1/auth/me",
            headers=self._headers(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()["data"]

    def get_health(self) -> dict:
        """Get system health status."""
        response = requests.get(
            f"{self.base_url}/api/v1/system/health",
            headers=self._headers(),
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.json()["data"]


def main():
    parser = argparse.ArgumentParser(description="Encryptor Simulator API client")
    parser.add_argument("--host", required=True, help="Management IP or hostname")
    parser.add_argument("--port", type=int, default=443, help="API port (default: 443)")
    parser.add_argument("--username", default="admin", help="Username (default: admin)")
    parser.add_argument("--password", required=True, help="User password")
    args = parser.parse_args()

    base_url = f"https://{args.host}:{args.port}"
    client = EncryptorSimClient(base_url, args.username, args.password)

    try:
        # 1. Authenticate
        client.login()

        # 2. Get user profile
        me = client.get_me()
        print(f"User: {me['username']} (ID: {me['userId']})")

        if me.get("requirePasswordChange"):
            print("WARNING: Password change required before normal operation.")
            sys.exit(1)

        # 3. Check system health
        health = client.get_health()
        print(f"System status: {health.get('status', 'unknown')}")

    except requests.HTTPError as e:
        print(f"API error: {e.response.status_code} - {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
