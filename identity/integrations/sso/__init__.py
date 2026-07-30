"""SSO integration factory.

Maps provider names to their concrete ``AbstractSSOService`` implementations.
This is the single entry point used by ``SSOService`` — it never imports
a concrete adapter directly.
"""

from __future__ import annotations

from identity.exceptions import UnsupportedSSOProviderError
from identity.integrations.sso.base import AbstractSSOService
from identity.integrations.sso.github import GitHubSSOService
from identity.models.sso import Provider

_SSO_REGISTRY: dict[str, type[AbstractSSOService]] = {
    Provider.GITHUB: GitHubSSOService,
}


def get_sso_service(provider_name: str) -> AbstractSSOService:
    """Resolve a provider name to a concrete SSO adapter instance.

    Args:
        provider_name: The SSO provider name (e.g. ``"GITHUB"``).

    Returns:
        An instance of the matching ``AbstractSSOService`` subclass.

    Raises:
        UnsupportedSSOProviderError: If the provider is not registered.
    """
    service_cls = _SSO_REGISTRY.get(provider_name)
    if service_cls is None:
        raise UnsupportedSSOProviderError(f"Unsupported SSO provider: {provider_name}")
    return service_cls()
