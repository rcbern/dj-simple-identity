"""Model re-exports for the Identity app.

Models are defined in individual modules and re-exported here so Django's
app registry discovers them via ``identity.models``.
"""

from identity.models.user import User

__all__ = ["User"]
