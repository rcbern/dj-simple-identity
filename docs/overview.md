# Overview

> **Section 1** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

This microservice is the single source of truth for identity, authentication, and session management. It is designed around a "Fat Services, Lean Models" philosophy. Database models act as pure data containers, while all business logic is isolated in dedicated service classes.

It sits behind a FastAPI Gateway (which handles rate limiting, CORS, and stateless Access Token validation). The Auth service communicates asynchronously with the rest of the system via Redis Streams.

## Related documents
- [Tech Stack](tech-stack.md)
- [Architectural Decisions Summary](architectural-decisions.md)
- [Directory Structure](directory-structure.md)