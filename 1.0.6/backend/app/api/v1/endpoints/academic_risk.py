from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.schemas.academic_risk import AcademicRiskAnalyzeRequest
from app.schemas.advisor import AcademicRiskAlertOut
from app.services.academic_advisor_service import AcademicAdvisorService

router = APIRouter()


@router.post("/analyze", response_model=AcademicRiskAlertOut)
def analyze_academic_risk(
    _: AcademicRiskAnalyzeRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AcademicRiskAlertOut:
    return AcademicAdvisorService().build_academic_risk(db, user)
