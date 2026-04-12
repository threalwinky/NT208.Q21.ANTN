from fastapi import APIRouter

from app.api.v1.endpoints import admin, advisor, announcements, auth, chat, dashboard, diary, health, reminders

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(reminders.router, prefix="/planner", tags=["planner"])
api_router.include_router(diary.router, prefix="/diary", tags=["diary"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
