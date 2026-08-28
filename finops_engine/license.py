"""
License verification utilities for Pro/Enterprise features.
"""

from finops_engine.config import settings
from finops_engine.errors import LicenseError


def verify_pro_license(feature_name: str) -> None:
    """
    Verify that a valid Pro/Enterprise license key is present.
    Raises LicenseError if the key is missing or invalid.
    """
    if not settings.license_key:
        raise LicenseError(
            f"The '{feature_name}' feature requires a Pro or Enterprise license. "
            "Please upgrade your license at GitHub Sponsors and set FINOP_LICENSE_KEY."
        )

    # Strip prefix if it exists to get the raw JWT token
    token = settings.license_key
    if token.startswith("FINOP_PRO_LICENSE_KEY_"):
        token = token[len("FINOP_PRO_LICENSE_KEY_") :]

    if not settings.license_public_key:
        raise LicenseError(f"Server is missing FINOP_LICENSE_PUBLIC_KEY to verify '{feature_name}'.")

    import jwt

    try:
        decoded = jwt.decode(token, settings.license_public_key, algorithms=["RS256"])
        if decoded.get("tier") not in ("pro", "team", "enterprise"):
            raise LicenseError(f"Your license tier '{decoded.get('tier')}' does not have access to '{feature_name}'.")
    except jwt.ExpiredSignatureError:
        raise LicenseError(f"Your FINOP_LICENSE_KEY has expired. Please renew to use '{feature_name}'.") from None
    except jwt.InvalidTokenError:
        raise LicenseError(
            f"Invalid FINOP_LICENSE_KEY for '{feature_name}'. Please verify your license key from GitHub Sponsors."
        ) from None
