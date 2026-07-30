"""Model re-exports for the Auth app.

Models are defined in individual modules and re-exported here so Django's
app registry discovers them via ``auth.models``.
"""

from auth.models.user import User

__all__ = ["User"]
