# Auth Microservice Architecture Specification

This is the split, cross-referenced version of the Auth microservice specification. Foundation and cross-cutting concerns are consolidated in a single file; API and domain concerns remain in dedicated files so you can load only the relevant slice into context when working on a given area.

## Table of Contents

### Foundations
| # | Document | Description |
|---|----------|-------------|
| 1 | [Overview](overview.md) | Single source of truth for identity, auth, and sessions; "Fat Services, Lean Models" philosophy; sits behind a FastAPI Gateway. Includes tech stack, architectural decisions, directory structure, testing strategy, and logging/observability. |

### Domains
| # | Document | Description |
|---|----------|-------------|
| 2 | [Identity & Users](domains/identity-and-users.md) | Custom `User` model (UUID PK, email-only, no `PermissionsMixin`), `UserManager`, `change_password`. |
| 3 | [Token Management & Security](domains/token-management.md) | Hybrid JWT strategy, lean `Token` model (no session families or revocation), `TokenService` (RS256 issue/decode). |
| 4 | [Authentication & Sessions](domains/authentication-and-sessions.md) | `AuthService`: access token generation, login (with MFA gate), logout, simple refresh rotation. |
| 5 | [Account Lifecycle & Events](domains/account-lifecycle.md) | `EventPublisher` (Redis Streams), `AccountService`: register, verify email, password reset. |
| 6 | [Multi-Factor Authentication (MFA)](domains/mfa.md) | `UserMFA` model (Fernet-encrypted TOTP), `UserMFAService`: enroll, verify, challenge issue/verify. |
| 7 | [Single Sign-On (SSO)](domains/sso.md) | `SocialAccount` model, SSO integration ABCs + factory, `SSOService` with email collision protection. |

### API
| # | Document | Description |
|---|----------|-------------|
| 8 | [REST API (Django Ninja)](api/rest-api.md) | Thin API layer: `JWTAuth` dependency, auth routes (login/refresh/logout), account, MFA, SSO routers. |

## How to use these docs
- Start at [Overview](overview.md) for orientation, tech stack, architectural decisions, directory structure, testing, and observability.
- When implementing a feature, open the relevant domain file plus its `Related documents` links.
- All links are relative; keep files under `docs/` so links stay valid.