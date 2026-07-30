# Auth Microservice Architecture Specification

This is the split, cross-referenced version of the Auth microservice specification. Each concern lives in its own file so you can load only the relevant slice into context when working on a given area. Every file ends with a `## Related documents` section linking to the files it depends on.

> The original monolithic document is preserved at [`to_split.md`](to_split.md) for reference. The files below are the source of truth going forward.

## Table of Contents

### Foundations
| # | Document | Description |
|---|----------|-------------|
| 1 | [Overview](overview.md) | Single source of truth for identity, auth, and sessions; "Fat Services, Lean Models" philosophy; sits behind a FastAPI Gateway. |
| 2 | [Tech Stack](tech-stack.md) | Django, Django Ninja, PostgreSQL, Redis Streams, security libs, testing, and logging dependencies. |
| 3 | [Architectural Decisions Summary](architectural-decisions.md) | Gateway-ready, RS256 JWTs, hybrid opaque refresh tokens, HttpOnly cookies & rotation, event-driven notifications, SSO DI, explicit `request_id` logging. |
| 4 | [Directory Structure](directory-structure.md) | Full project tree: `certs/`, `auth/` (models, services, infrastructure, integrations, api, tests), and project settings. |

### Domains
| # | Document | Description |
|---|----------|-------------|
| 5 | [Identity & Users](domains/identity-and-users.md) | Custom `User` model (UUID PK, email-only, no `PermissionsMixin`), `UserManager`, `change_password`. |
| 6 | [Token Management & Security](domains/token-management.md) | Hybrid JWT strategy, `Token` model (rotation, reuse detection, attempts), `TokenService` (RS256 issue/decode). |
| 7 | [Authentication & Sessions](domains/authentication-and-sessions.md) | `AuthService`: access token generation, login (with MFA gate), logout, refresh rotation. |
| 8 | [Account Lifecycle & Events](domains/account-lifecycle.md) | `EventPublisher` (Redis Streams), `AccountService`: register, verify email, password reset. |
| 9 | [Multi-Factor Authentication (MFA)](domains/mfa.md) | `UserMFA` model (Fernet-encrypted TOTP), `UserMFAService`: enroll, verify, challenge issue/verify. |
| 10 | [Single Sign-On (SSO)](domains/sso.md) | `SocialAccount` model, SSO integration ABCs + factory, `SSOService` with email collision protection. |

### Layers & Cross-Cutting
| # | Document | Description |
|---|----------|-------------|
| 11 | [REST API (Django Ninja)](api/rest-api.md) | Thin API layer: `JWTAuth` dependency, auth routes (login/refresh/logout + cookies), health route. |
| 12 | [Testing Strategy](testing.md) | pytest + pytest-django, factories, service tests with mocks, `fakeredis` infrastructure tests. |
| 13 | [Logging and Observability](observability.md) | 12-Factor JSON logging to stdout, explicit `request_id` correlation, settings, middleware, service usage. |

## How to use these docs
- Start at [Overview](overview.md) and [Architectural Decisions Summary](architectural-decisions.md) for orientation.
- When implementing a feature, open the relevant domain file plus its `Related documents` links.
- All links are relative; keep files under `docs/` so links stay valid.