"""
Utility script to generate JWT license keys for FinOps Pro/Enterprise users.

Usage:
  python -m scripts.generate_license --tier pro --days 30

Outputs a cryptographically signed JWT and the corresponding public key if needed.
"""

import argparse
import datetime

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem


def generate_license(tier: str, days: int, private_key_pem: bytes) -> str:
    payload = {
        "tier": tier,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days),
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    token = jwt.encode(payload, private_key_pem, algorithm="RS256")
    return f"FINOP_PRO_LICENSE_KEY_{token}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FinOps Engine License Keys")
    parser.add_argument("--tier", choices=["pro", "team", "enterprise"], default="pro")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    private_pem, public_pem = generate_key_pair()

    print("\n--- NEW KEY PAIR GENERATED ---")
    print("\nKeep this PRIVATE KEY safe! (Do not share):")
    print(private_pem.decode("utf-8"))

    print("\nSet this PUBLIC KEY in FINOP_LICENSE_PUBLIC_KEY env var:")
    print(public_pem.decode("utf-8"))

    token = generate_license(args.tier, args.days, private_pem)
    print(f"\nShare this LICENSE KEY with the user (Tier: {args.tier}, Valid for {args.days} days):")
    print(token)
    print("\n------------------------------\n")
