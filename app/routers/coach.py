from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..schemas import CoachIn
from ..security import current_user
from ..services.coach import ask_openai, detect_language

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.post("/ask")
def ask(body: CoachIn, request: Request, db: Session = Depends(get_db)):
    current_user(db, request)
    settings = get_settings()
    answer, source, used_fallback = ask_openai(settings, body.question.strip())
    return {
        "answer": answer,
        "source": source,
        "used_fallback": used_fallback,
        "detected_language": detect_language(body.question),
        "disclaimer": "Educational explanation only. Not personalized investment advice.",
    }
