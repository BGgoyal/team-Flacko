def project_sip(monthly: float, months: int, annual_return_pct: float) -> dict:
    invested = monthly * months
    monthly_rate = (annual_return_pct / 100.0) / 12.0
    if monthly_rate == 0:
        future_value = invested
    else:
        future_value = monthly * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    return {
        "monthly_contribution": monthly,
        "duration_months": months,
        "assumed_annual_return_pct": annual_return_pct,
        "invested": round(invested, 2),
        "future_value": round(future_value, 2),
        "estimated_gain": round(future_value - invested, 2),
    }


def sip_bundle(monthly: float, months: int, assumed_return: float, goal_amount: float) -> dict:
    assumed = project_sip(monthly, months, assumed_return)
    zero = project_sip(monthly, months, 0)
    return {
        "goal_amount": goal_amount,
        "hypothetical": assumed,
        "zero_return": zero,
        "reaches_goal_hypothetical": assumed["future_value"] >= goal_amount if goal_amount else False,
        "reaches_goal_zero_return": zero["future_value"] >= goal_amount if goal_amount else False,
        "disclaimer": (
            "These figures are hypothetical illustrations, not forecasts. "
            "Returns are not guaranteed. Markets can fall. This is education, not advice."
        ),
    }
