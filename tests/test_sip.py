from app.services.sip import project_sip, sip_bundle


def test_zero_return_is_contributions_only():
    result = project_sip(1000, 12, 0)
    assert result["invested"] == 12000
    assert result["future_value"] == 12000
    assert result["estimated_gain"] == 0


def test_positive_return_exceeds_contributions():
    result = project_sip(1000, 12, 12)
    assert result["future_value"] > result["invested"]


def test_bundle_includes_zero_and_disclaimer():
    bundle = sip_bundle(2000, 24, 8, 60000)
    assert bundle["zero_return"]["assumed_annual_return_pct"] == 0
    assert "not guaranteed" in bundle["disclaimer"].lower()
    assert bundle["hypothetical"]["future_value"] >= bundle["zero_return"]["future_value"]
