import re

import httpx

from ..config import Settings

E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_in_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10:
        return f"+91{digits}"
    if raw.strip().startswith("+") and E164.match(raw.strip()):
        return raw.strip()
    raise ValueError("Enter a valid Indian mobile number (10 digits).")


def send_otp(settings: Settings, phone: str) -> None:
    if not settings.twilio_configured:
        raise RuntimeError("SMS verification is not configured on the server.")
    url = f"https://verify.twilio.com/v2/Services/{settings.twilio_verify_service_sid}/Verifications"
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            url,
            data={"To": phone, "Channel": "sms"},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
    if response.status_code >= 400:
        raise RuntimeError("The SMS provider could not send a verification code. Check Twilio Verify setup.")


def check_otp(settings: Settings, phone: str, code: str) -> bool:
    if not settings.twilio_configured:
        raise RuntimeError("SMS verification is not configured on the server.")
    url = f"https://verify.twilio.com/v2/Services/{settings.twilio_verify_service_sid}/VerificationCheck"
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            url,
            data={"To": phone, "Code": code},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
    if response.status_code >= 400:
        raise RuntimeError("The SMS provider could not check that code.")
    payload = response.json()
    return payload.get("status") == "approved"
