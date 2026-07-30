# Architectural Decisions Summary

> **Section 3** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

1. **Gateway-Ready Architecture:** The Auth service does not handle rate limiting, CORS, or internal gRPC token validation. A FastAPI Gateway sits in front, holding the JWT Public Key to validate Access Tokens locally before routing requests.
2. **Asymmetric JWTs (RS256):** The Auth service signs stateless Access Tokens with an RSA Private Key. The Gateway and other microservices verify them using the Public Key.
3. **Hybrid Opaque Refresh Tokens:** Refresh tokens are delivered to the client as JWTs wrapping an opaque string. The database stores a SHA-256 hash of that string.
4. **Simple Rotation (No Session Families):** On `/refresh`, the old token is deleted and a new one is issued. The implementation intentionally omits session-family tracking and reuse detection — brute-force protection is delegated to the gateway's rate limiter, and the lean `Token` model keeps the schema minimal.
5. **Event-Driven Notifications:** The Auth service **does not send emails**. It publishes events to Redis Streams.
6. **Dependency Inversion for SSO:** SSO integrations rely on Abstract Base Classes, allowing easy swapping of providers without touching business logic.
7. **Explicit `request_id` Logging:** Correlation IDs are passed explicitly through function arguments to `extra` in the logger, avoiding `contextvars`.
8. **Custom Domain Exceptions:** All services raise semantically meaningful custom exceptions (e.g. `InvalidCredentialsError`, `TokenInvalidError`, `SSOEmailCollisionError`) instead of bare `ValueError`/`PermissionError`, making API-layer error handling cleaner.

## Related documents
- [Overview](overview.md)
- [Tech Stack](tech-stack.md)
- [Directory Structure](directory-structure.md)
- [Token Management & Security](domains/token-management.md)
- [Authentication & Sessions](domains/authentication-and-sessions.md)
- [Account Lifecycle & Events](domains/account-lifecycle.md)
- [Single Sign-On (SSO)](domains/sso.md)
- [Logging and Observability](observability.md)