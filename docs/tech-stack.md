# Tech Stack

> **Section 2** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

* **Framework:** Django
* **REST API:** Django Ninja (Pydantic validation)
* **Database:** PostgreSQL (implied)
* **Cache/Message Broker:** Redis (Redis Streams for Event-Driven Architecture)
* **Security Libraries:** `PyJWT`, `pyotp`, `cryptography` (Fernet), Python `secrets` & `hashlib`
* **Testing:** `pytest`, `pytest-django`, `pytest-mock`, `factory-boy`, `fakeredis`
* **Logging:** `python-json-logger`

## Related documents
- [Overview](overview.md)
- [Architectural Decisions Summary](architectural-decisions.md)
- [Testing Strategy](testing.md)
- [Logging and Observability](observability.md)