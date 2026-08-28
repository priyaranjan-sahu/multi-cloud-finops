"""
Unit tests for the license verification gate.

Covers:
- Missing key raises LicenseError
- Invalid prefix raises LicenseError
- Valid key passes through silently (happy path)
- All five Pro CLI entry points are gated
"""

import datetime

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from finops_engine.errors import LicenseError
from finops_engine.license import verify_pro_license


@pytest.fixture(scope="module")
def rsa_keys():
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


@pytest.fixture
def valid_token(rsa_keys):
    private_pem, _ = rsa_keys
    payload = {
        "tier": "pro",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30),
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")


def test_verify_pro_license_raises_when_key_missing(monkeypatch):
    """No license key set → LicenseError with Sponsors upgrade message."""
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", "")
    with pytest.raises(LicenseError, match="requires a Pro or Enterprise license"):
        verify_pro_license("Test Feature")


def test_verify_pro_license_raises_when_public_key_missing(monkeypatch, valid_token):
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", f"FINOP_PRO_LICENSE_KEY_{valid_token}")
    monkeypatch.setattr(settings, "license_public_key", "")
    with pytest.raises(LicenseError, match="Server is missing FINOP_LICENSE_PUBLIC_KEY"):
        verify_pro_license("Test Feature")


def test_verify_pro_license_raises_on_invalid_token(monkeypatch, rsa_keys):
    from finops_engine.config import settings

    _, public_pem = rsa_keys
    monkeypatch.setattr(settings, "license_key", "FINOP_PRO_LICENSE_KEY_WRONG_TOKEN")
    monkeypatch.setattr(settings, "license_public_key", public_pem.decode("utf-8"))
    with pytest.raises(LicenseError, match="Invalid FINOP_LICENSE_KEY"):
        verify_pro_license("Test Feature")


def test_verify_pro_license_passes_with_valid_key(monkeypatch, rsa_keys, valid_token):
    """Valid JWT → no exception raised (happy path)."""
    from finops_engine.config import settings

    _, public_pem = rsa_keys
    monkeypatch.setattr(settings, "license_key", f"FINOP_PRO_LICENSE_KEY_{valid_token}")
    monkeypatch.setattr(settings, "license_public_key", public_pem.decode("utf-8"))
    # Should not raise
    verify_pro_license("Test Feature")


def test_cli_anomaly_detection_is_gated(monkeypatch):
    """scripts.anomaly_detection must call verify_pro_license before doing any work."""
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", "")
    from scripts.anomaly_detection import run_anomaly_detection

    with pytest.raises(LicenseError):
        run_anomaly_detection(days=7)


def test_cli_cost_forecasting_is_gated(monkeypatch):
    """scripts.cost_forecasting must call verify_pro_license before doing any work."""
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", "")
    from scripts.cost_forecasting import run_cost_prediction

    with pytest.raises(LicenseError):
        run_cost_prediction(forecast_days=7, history_days=14)


def test_cli_rightsizing_is_gated(monkeypatch):
    """scripts.rightsizing must call verify_pro_license before doing any work."""
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", "")
    from scripts.rightsizing import run_rightsizing_analysis

    with pytest.raises(LicenseError):
        run_rightsizing_analysis(days=7)


def test_cli_spot_optimization_is_gated(monkeypatch):
    """scripts.spot_optimization must call verify_pro_license before doing any work."""
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", "")
    from scripts.spot_optimization import analyze_spot_opportunities

    with pytest.raises(LicenseError):
        analyze_spot_opportunities(days=7)


def test_cli_export_recommendations_is_gated(monkeypatch):
    """scripts.export_recommendations must call verify_pro_license before doing any work."""
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "license_key", "")
    from scripts.export_recommendations import export_rightsizing_recommendations

    with pytest.raises(LicenseError):
        export_rightsizing_recommendations(days=7)
