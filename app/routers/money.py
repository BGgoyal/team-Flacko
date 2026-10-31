from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BudgetCategory, MoneyProfile, SipPlan
from ..schemas import CategoryIn, CategoryUpdate, ProfileIn, SipIn
from ..security import current_user
from ..services.sip import sip_bundle
from .auth import seed_categories

router = APIRouter(prefix="/api", tags=["money"])

DATA_NOTICE = (
    "FinCoach stores your name, income type, monthly income and expenses, current savings, "
    "one goal, budget category names and amounts, and SIP simulator inputs so the screens can reload. "
    "It does not store broker passwords. Sign-in uses a session cookie on this device."
)


def _profile_out(profile: MoneyProfile, name: str) -> dict:
    return {
        "name": name,
        "monthly_income": profile.monthly_income,
        "income_type": profile.income_type,
        "monthly_expenses": profile.monthly_expenses,
        "current_savings": profile.current_savings,
        "goal_title": profile.goal_title,
        "goal_amount": profile.goal_amount,
        "what_is_saved": DATA_NOTICE,
    }


@router.get("/profile")
def get_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    if not user.profile:
        return {"profile": None, "what_is_saved": DATA_NOTICE}
    return {"profile": _profile_out(user.profile, user.name), "what_is_saved": DATA_NOTICE}


@router.put("/profile")
def put_profile(body: ProfileIn, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    user.name = body.name.strip()
    profile = user.profile
    if not profile:
        profile = MoneyProfile(user_id=user.id)
        db.add(profile)
    profile.monthly_income = body.monthly_income
    profile.income_type = body.income_type
    profile.monthly_expenses = body.monthly_expenses
    profile.current_savings = body.current_savings
    profile.goal_title = body.goal_title.strip()
    profile.goal_amount = body.goal_amount
    db.commit()
    db.refresh(user)
    seed_categories(db, user, body.monthly_expenses)
    db.refresh(user)
    return {"profile": _profile_out(user.profile, user.name), "what_is_saved": DATA_NOTICE}


@router.get("/budget")
def get_budget(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    income = user.profile.monthly_income if user.profile else 0
    cats = [{"id": c.id, "name": c.name, "planned_amount": c.planned_amount} for c in user.categories]
    planned = sum(c["planned_amount"] for c in cats)
    return {
        "monthly_income": income,
        "categories": cats,
        "planned_spending": planned,
        "remaining_income": round(income - planned, 2),
        "note": "Planned amounts are your inputs, not bank transactions. Remaining income is an estimate.",
    }


@router.post("/budget/categories")
def add_category(body: CategoryIn, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    existing = (
        db.query(BudgetCategory)
        .filter(BudgetCategory.user_id == user.id, BudgetCategory.name == body.name.strip())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="A category with that name already exists.")
    cat = BudgetCategory(user_id=user.id, name=body.name.strip(), planned_amount=body.planned_amount)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "planned_amount": cat.planned_amount}


@router.patch("/budget/categories/{cat_id}")
def update_category(cat_id: int, body: CategoryUpdate, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    cat = db.get(BudgetCategory, cat_id)
    if not cat or cat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Category not found.")
    if body.name is not None:
        cat.name = body.name.strip()
    if body.planned_amount is not None:
        cat.planned_amount = body.planned_amount
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "planned_amount": cat.planned_amount}


@router.delete("/budget/categories/{cat_id}")
def delete_category(cat_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    cat = db.get(BudgetCategory, cat_id)
    if not cat or cat.user_id != user.id:
        raise HTTPException(status_code=404, detail="Category not found.")
    db.delete(cat)
    db.commit()
    return {"ok": True}


@router.get("/overview")
def overview(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    if not user.profile:
        raise HTTPException(status_code=404, detail="Complete your money profile first.")
    p = user.profile
    cats = [{"name": c.name, "planned_amount": c.planned_amount} for c in user.categories]
    planned = sum(c["planned_amount"] for c in cats)
    remaining = round(p.monthly_income - planned, 2)
    progress = None
    if p.goal_amount > 0:
        progress = min(100.0, round((p.current_savings / p.goal_amount) * 100, 2))
    outlook = []
    running = p.current_savings
    for month in range(0, 13):
        outlook.append({"month": month, "estimated_savings": round(running, 2)})
        running += remaining
    return {
        "name": user.name,
        "income_type": p.income_type,
        "monthly_income": p.monthly_income,
        "planned_expenses": planned,
        "profile_expenses_input": p.monthly_expenses,
        "remaining_amount": remaining,
        "categories": cats,
        "goal_title": p.goal_title,
        "goal_amount": p.goal_amount,
        "current_savings": p.current_savings,
        "goal_progress_pct": progress,
        "savings_outlook": outlook,
        "assumptions": [
            "Remaining amount = monthly income minus planned budget categories (not live bank data).",
            "Savings outlook adds that remaining amount each month to current savings, with 0% return.",
            "If remaining is negative, the outlook shows savings shrinking — an estimate, not a prediction.",
            "FinCoach is educational software, not a regulated financial adviser.",
        ],
    }


@router.get("/sip")
def get_sip(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    plan = user.sip
    if not plan:
        return {"plan": None, "projection": None}
    projection = sip_bundle(
        plan.monthly_contribution, plan.duration_months, plan.assumed_return_annual, plan.goal_amount
    )
    return {
        "plan": {
            "goal_amount": plan.goal_amount,
            "monthly_contribution": plan.monthly_contribution,
            "duration_months": plan.duration_months,
            "assumed_return_annual": plan.assumed_return_annual,
        },
        "projection": projection,
    }


@router.put("/sip")
def put_sip(body: SipIn, request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    plan = user.sip
    if not plan:
        plan = SipPlan(user_id=user.id)
        db.add(plan)
    plan.goal_amount = body.goal_amount
    plan.monthly_contribution = body.monthly_contribution
    plan.duration_months = body.duration_months
    plan.assumed_return_annual = body.assumed_return_annual
    db.commit()
    db.refresh(plan)
    return {
        "plan": {
            "goal_amount": plan.goal_amount,
            "monthly_contribution": plan.monthly_contribution,
            "duration_months": plan.duration_months,
            "assumed_return_annual": plan.assumed_return_annual,
        },
        "projection": sip_bundle(
            plan.monthly_contribution, plan.duration_months, plan.assumed_return_annual, plan.goal_amount
        ),
    }
