def test_profile_budget_overview_sip(authed_client):
    saved = authed_client.put(
        "/api/profile",
        json={
            "name": "Asha",
            "monthly_income": 40000,
            "income_type": "first_job",
            "monthly_expenses": 28000,
            "current_savings": 15000,
            "goal_title": "Emergency buffer",
            "goal_amount": 80000,
        },
    )
    assert saved.status_code == 200
    assert "stores your name" in saved.json()["what_is_saved"].lower()

    budget = authed_client.get("/api/budget").json()
    assert budget["monthly_income"] == 40000
    assert budget["planned_spending"] > 0
    cat = authed_client.post("/api/budget/categories", json={"name": "Subscriptions", "planned_amount": 499})
    assert cat.status_code == 200
    cat_id = cat.json()["id"]
    authed_client.patch(f"/api/budget/categories/{cat_id}", json={"planned_amount": 299})
    authed_client.delete(f"/api/budget/categories/{cat_id}")

    overview = authed_client.get("/api/overview").json()
    assert overview["monthly_income"] == 40000
    assert len(overview["savings_outlook"]) == 13
    assert any("not a regulated" in a.lower() for a in overview["assumptions"])

    sip = authed_client.put(
        "/api/sip",
        json={
            "goal_amount": 100000,
            "monthly_contribution": 3000,
            "duration_months": 24,
            "assumed_return_annual": 8,
        },
    )
    assert sip.status_code == 200
    proj = sip.json()["projection"]
    assert proj["zero_return"]["future_value"] == 72000
    assert "hypothetical" in proj["disclaimer"].lower()
