# Architectural Decisions Summary

> **Section 3** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

1. **Gateway-Ready Architecture:** The Auth service does not handle rate limiting, CORS, or internal gRPC token validation. A FastAPI Gateway sits in front, holding the JWT Public Key to validate Access Tokens locally before routing requests.
2. **Asymmetric JWTs (RS256):** The Auth service signs stateless Access Tokens with an RSA Private Key. The Gateway and other microservices verify them using the Public Key.
3. **Hybrid Opaque Refresh Tokens:** Refresh tokens are delivered to the client as JWTs wrapping an opaque string. The database stores a SHA-256 hash of that string.
4. **HttpOnly Cookies & Rotation:** Refresh tokens are stored in `HttpOnly`, `Secure`, `SameSite=Strict` cookies to prevent XSS. Tokens are rotated on every `/refresh` call, and reuse of an old token triggers immediate session family revocation.
5. **Event-Driven Notifications:** The Auth service **does not send emails**. It publishes events to Redis Streams.
6. **Dependency Inversion for SSO:** SSO integrations rely on Abstract Base Classes, allowing easy swapping of providers without touching business logic.
7. **Explicit `request_id` Logging:** Correlation IDs are passed explicitly through function arguments to `extra` in the logger, avoiding `contextvars`.

## Related documents
- [Overview](overview.md)
- [Tech Stack](tech-stack.md)
- [Directory Structure](directory-structure.md)
- [Token Management & Security](domains/token-management.md)
- [Authentication & Sessions](domains/authentication-and-sessions.md)
- [Account Lifecycle & Events](domains/account-lifecycle.md)
- [Single Sign-On (SSO)](domains/sso.md)
- [Logging and Observability](observability.md)