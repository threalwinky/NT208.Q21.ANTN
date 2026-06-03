from fastapi import APIRouter

from app.api.v1.endpoints import (
    academic_risk,
    admin,
    advisor,
    announcements,
    auth,
    chat,
    courses,
    dashboard,
    diary,
    documents,
    feedback,
    gpa,
    health,
    notifications,
    profile,
    reminders,
    revision,
    search,
    spotify,
    study_plans,
    wellbeing,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(gpa.router, prefix="/gpa", tags=["gpa"])
api_router.include_router(academic_risk.router, prefix="/academic-risk", tags=["academic-risk"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(feedback.admin_router, prefix="/admin/feedback", tags=["admin"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(reminders.router, prefix="/planner", tags=["planner"])
api_router.include_router(study_plans.router, prefix="/study-plans", tags=["study-plans"])
api_router.include_router(diary.router, prefix="/diary", tags=["diary"])
api_router.include_router(revision.router, prefix="/revision", tags=["revision"])
api_router.include_router(wellbeing.router, prefix="/wellbeing", tags=["wellbeing"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(spotify.router, prefix="/integrations/spotify", tags=["spotify"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
