# Tech Stack

> **Section 2** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

* **Framework:** Django 6.0+
* **REST API:** Django Ninja 1.6+ (Pydantic validation)
* **Database:** PostgreSQL (via `psycopg[binary]`)
* **Cache/Message Broker:** Redis 8.1+ (Redis Streams for Event-Driven Architecture)
* **Security Libraries:** `PyJWT` (RS256), `pyotp` (TOTP), `cryptography` (Fernet), `argon2-cffi` (password hashing), Python `secrets` & `hashlib`
* **Testing:** `pytest`, `pytest-django`, `pytest-mock`, `factory-boy`, `fakeredis`
* **Linting & Type Checking:** `ruff` (lint + format), `ty` (static type checking)
* **Logging:** `python-json-logger`
* **Package Management:** `uv` (Astral)

## Related documents
- [Overview](overview.md)
- [Architectural Decisions Summary](architectural-decisions.md)
- [Testing Strategy](testing.md)
- [Logging and Observability](observability.md)