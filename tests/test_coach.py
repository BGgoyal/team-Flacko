from app.services.coach import detect_language, fallback_answer


def test_language_detection():
    assert detect_language("SIP kya hota hai mujhe samjhao") == "hinglish"
    assert detect_language("एसआईपी क्या होता है") == "hi"
    assert detect_language("How does a budget leftover work?") == "en"


def test_fallback_answers_the_question_not_one_keyword():
    sip = fallback_answer("If I put 2000 a month for 2 years in a SIP, is the return guaranteed?")
    stocks = fallback_answer("Should I buy the best stock for my budget this week?")
    assert "2000" in sip or "SIP" in sip or "sip" in sip.lower()
    assert "guaranteed" in sip.lower() or "not a promise" in sip.lower() or "not guaranteed" in sip.lower() or "classroom" in sip.lower()
    assert "best stock" in stocks.lower() or "specific stock" in stocks.lower()
    assert sip != stocks


def test_coach_endpoint_labels_fallback(authed_client):
    r = authed_client.post("/api/coach/ask", json={"question": "Mujhe emergency fund kaise sochna chahiye?"})
    assert r.status_code == 200
    body = r.json()
    assert body["used_fallback"] is True
    assert body["source"] == "limited_demo_fallback"
    assert "emergency" in body["answer"].lower() or "Emergency" in body["answer"]


def test_openai_request_uses_server_api_key(monkeypatch):
    from app.config import Settings
    from app.services.coach import ask_openai

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "A concise educational answer."}}]}

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            assert url == "https://api.openai.com/v1/chat/completions"
            assert kwargs["headers"]["Authorization"] == "Bearer server-openai-key"
            return Response()

    monkeypatch.setattr("app.services.coach.httpx.Client", Client)
    answer, source, used_fallback = ask_openai(
        Settings(openai_api_key="server-openai-key"),
        "Explain what a budget is.",
    )

    assert answer == "A concise educational answer."
    assert source == "openai"
    assert used_fallback is False
