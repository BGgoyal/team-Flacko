def test_register_login_me_and_logout(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "patel@example.com", "password": "secret123", "name": "Patel"},
    )
    assert r.status_code == 200
    assert "fincoach_session" in r.cookies
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "patel@example.com"
    bad = client.post("/api/auth/login", json={"email": "patel@example.com", "password": "wrongpass"})
    assert bad.status_code == 401
    client.post("/api/auth/logout")
    me2 = client.get("/api/auth/me")
    assert me2.status_code == 401


def test_otp_setup_state_when_twilio_missing(client):
    status = client.get("/api/auth/status").json()
    assert status["twilio_configured"] is False
    start = client.post("/api/auth/otp/start", json={"phone": "9876543210"})
    assert start.status_code == 503
    assert "fake" in start.json()["detail"].lower()
    verify = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": "123456"})
    assert verify.status_code == 503


def test_password_is_hashed():
    from app.security import hash_password, verify_password

    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("nope", hashed)
