"""GitHub SSO integration adapter.

Exchanges an OAuth authorization code for a GitHub access token, then
fetches the authenticated user's GitHub ID and primary email.
"""

from __future__ import annotations

import httpx
from django.conf import settings

from identity.exceptions import SSOError
from identity.integrations.sso.base import AbstractSSOService

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class GitHubSSOService(AbstractSSOService):
    """Concrete SSO adapter for GitHub OAuth.

    Uses ``httpx`` to make synchronous HTTP requests to GitHub's API.
    """

    def exchange_code_and_get_user(self, code: str) -> tuple[str, str]:
        """Exchange a GitHub OAuth code for the user's ID and email.

        Args:
            code: The authorization code from the GitHub OAuth callback.

        Returns:
            A ``(provider_user_id, provider_email)`` tuple.

        Raises:
            SSOError: If the code exchange or user fetch fails.
        """
        access_token = self._exchange_code_for_token(code)
        provider_user_id, provider_email = self._fetch_user(access_token)
        return provider_user_id, provider_email

    def _exchange_code_for_token(self, code: str) -> str:
        """Exchange the OAuth code for a GitHub access token.

        Args:
            code: The authorization code from the callback.

        Returns:
            The GitHub access token string.

        Raises:
            SSOError: If the token exchange fails.
        """
        try:
            response = httpx.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SSOError(f"GitHub token exchange failed: {exc}") from exc

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise SSOError("GitHub did not return an access token.")
        return access_token

    def _fetch_user(self, access_token: str) -> tuple[str, str]:
        """Fetch the GitHub user's ID and primary email.

        Args:
            access_token: The GitHub OAuth access token.

        Returns:
            A ``(provider_user_id, provider_email)`` tuple.

        Raises:
            SSOError: If the user fetch fails or email is not found.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            user_response = httpx.get(GITHUB_USER_URL, headers=headers, timeout=10.0)
            user_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SSOError(f"GitHub user fetch failed: {exc}") from exc

        user_data = user_response.json()
        provider_user_id = str(user_data.get("id", ""))
        if not provider_user_id:
            raise SSOError("GitHub did not return a user ID.")

        # Fetch primary email (may differ from the public profile email)
        try:
            emails_response = httpx.get(
                GITHUB_EMAILS_URL, headers=headers, timeout=10.0
            )
            emails_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SSOError(f"GitHub email fetch failed: {exc}") from exc

        emails = emails_response.json()
        primary_email = self._get_primary_email(emails)
        if not primary_email:
            raise SSOError("No verified primary email found on GitHub.")

        return provider_user_id, primary_email

    @staticmethod
    def _get_primary_email(emails: list[dict[str, object]]) -> str | None:
        """Extract the primary verified email from GitHub's email list.

        Args:
            emails: The list of email objects from the GitHub API.

        Returns:
            The primary verified email string, or ``None``.
        """
        for email in emails:
            is_primary = email.get("primary", False)
            is_verified = email.get("verified", False)
            email_addr = email.get("email", "")
            if is_primary and is_verified and isinstance(email_addr, str):
                return email_addr
        return None
