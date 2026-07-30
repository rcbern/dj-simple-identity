#!/usr/bin/env python
"""Generate development RSA key pair and Fernet key for local Auth service.

Run once after cloning::

    python scripts/generate_keys.py

Outputs:
    - ``certs/private.pem``  — RSA private key (RS256 signing)
    - ``certs/public.pem``   — RSA public key (RS256 verification)
    - Prints a Fernet key for ``MFA_ENCRYPTION_KEY`` in ``.env``

These keys are for **local development only**. Never commit them.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERTS_DIR = Path(__file__).resolve().parent.parent / "certs"


def generate_rsa_keypair() -> tuple[str, str]:
    """Generate a 2048-bit RSA key pair and return PEM-encoded strings.

    Returns:
        A ``(private_pem, public_pem)`` tuple of UTF-8 strings.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def main() -> None:
    """Generate dev keys and write them to ``certs/``."""
    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    private_path = CERTS_DIR / "private.pem"
    public_path = CERTS_DIR / "public.pem"

    if private_path.exists() or public_path.exists():
        print("Keys already exist in certs/. Remove them to regenerate.")
        sys.exit(0)

    private_pem, public_pem = generate_rsa_keypair()
    private_path.write_text(private_pem)
    public_path.write_text(public_pem)

    fernet_key = Fernet.generate_key().decode("utf-8")

    print("Dev RSA key pair generated:")
    print(f"  {private_path}")
    print(f"  {public_path}")
    print()
    print("Add this Fernet key to your .env as MFA_ENCRYPTION_KEY:")
    print(f"  {fernet_key}")


if __name__ == "__main__":
    main()
