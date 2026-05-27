from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.users import User
from app.schemas.advisor import AcademicRiskAlertOut, AdvisorOverviewOut, DegreeAuditOut, SemesterPlanningOut
from app.services.academic_advisor_service import AcademicAdvisorService

router = APIRouter()


@router.get("/overview", response_model=AdvisorOverviewOut)
def advisor_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AdvisorOverviewOut:
    try:
        return AcademicAdvisorService().build_overview(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit", response_model=DegreeAuditOut)
def degree_audit(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DegreeAuditOut:
    try:
        return AcademicAdvisorService().build_degree_audit(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/plan", response_model=SemesterPlanningOut)
def semester_plan(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SemesterPlanningOut:
    try:
        return AcademicAdvisorService().build_semester_planning(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/risk", response_model=AcademicRiskAlertOut)
def academic_risk(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AcademicRiskAlertOut:
    try:
        return AcademicAdvisorService().build_academic_risk(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
