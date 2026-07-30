"""Abstract base class for SSO provider integrations.

Defines the interface that all SSO provider adapters must implement.
This follows the Dependency Inversion Principle — the ``SSOService``
depends on this abstraction, not on any concrete provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractSSOService(ABC):
    """Abstract interface for an SSO provider integration.

    Concrete implementations (e.g. ``GitHubSSOService``) exchange an
    OAuth authorization code for an access token and fetch the user's
    provider identity (user ID + email).
    """

    @abstractmethod
    def exchange_code_and_get_user(self, code: str) -> tuple[str, str]:
        """Exchange an OAuth code for the provider user's ID and email.

        Args:
            code: The authorization code from the OAuth callback.

        Returns:
            A ``(provider_user_id, provider_email)`` tuple.

        Raises:
            SSOError: If the code exchange or user fetch fails.
        """
        ...
