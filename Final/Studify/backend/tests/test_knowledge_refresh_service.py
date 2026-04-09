from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.services.knowledge_refresh_service import KnowledgeRefreshService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_refresh_schedule_defaults_to_due_when_never_run() -> None:
    db = make_session()
    try:
        service = KnowledgeRefreshService()
        assert service.should_queue_periodic_run(db) is True
    finally:
        db.close()


def test_refresh_schedule_waits_until_interval_passes() -> None:
    db = make_session()
    try:
        service = KnowledgeRefreshService()
        service.ensure_configs(db)
        runtime_config = db.query(app.models.wellbeing.SystemConfig).filter_by(key="knowledge_refresh_runtime").first()
        assert runtime_config is not None
        runtime_config.value_json = {
            "status": "READY",
            "last_success_at": datetime.now(timezone.utc).isoformat(),
            "next_run_at": (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat(),
        }
        db.commit()

        assert service.should_queue_periodic_run(db) is False
    finally:
        db.close()


def test_refresh_schedule_becomes_due_after_interval() -> None:
    db = make_session()
    try:
        service = KnowledgeRefreshService()
        service.ensure_configs(db)
        runtime_config = db.query(app.models.wellbeing.SystemConfig).filter_by(key="knowledge_refresh_runtime").first()
        assert runtime_config is not None
        runtime_config.value_json = {
            "status": "READY",
            "last_success_at": (datetime.now(timezone.utc) - timedelta(hours=73)).isoformat(),
            "next_run_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        }
        db.commit()

        assert service.should_queue_periodic_run(db) is True
    finally:
        db.close()
