from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.knowledge import DataSource
from app.models.users import User, UserRole
from app.models.wellbeing import InAppNotification, SystemConfig
from app.scripts.import_snapshot_data import import_snapshot_records
from app.scripts.train_corpus import collect_training_corpus


SCHEDULE_CONFIG_KEY = "knowledge_refresh_schedule"
RUNTIME_CONFIG_KEY = "knowledge_refresh_runtime"

DEFAULT_SCHEDULE = {
    "enabled": True,
    "interval_hours": 72,
    "target_documents": 30,
    "retry_after_hours_on_failure": 6,
}

DEFAULT_RUNTIME = {
    "status": "IDLE",
    "last_started_at": None,
    "last_completed_at": None,
    "last_success_at": None,
    "last_trigger": None,
    "last_message": "Chưa có lượt làm mới corpus nào.",
    "next_run_at": None,
    "last_result": None,
}


class KnowledgeRefreshService:
    def _get_or_create_config(self, db: Session, key: str, default_value: dict, description: str) -> SystemConfig:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config is None:
            config = SystemConfig(key=key, value_json=default_value, description=description)
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    def ensure_configs(self, db: Session) -> tuple[SystemConfig, SystemConfig]:
        schedule = self._get_or_create_config(
            db,
            SCHEDULE_CONFIG_KEY,
            DEFAULT_SCHEDULE.copy(),
            "Lịch làm mới corpus RAG định kỳ từ các nguồn UIT.",
        )
        runtime = self._get_or_create_config(
            db,
            RUNTIME_CONFIG_KEY,
            DEFAULT_RUNTIME.copy(),
            "Trạng thái lượt làm mới corpus gần nhất.",
        )
        return schedule, runtime

    def get_schedule(self, db: Session) -> dict:
        schedule_config, _ = self.ensure_configs(db)
        return {**DEFAULT_SCHEDULE, **(schedule_config.value_json or {})}

    def get_runtime(self, db: Session) -> dict:
        _, runtime_config = self.ensure_configs(db)
        return {**DEFAULT_RUNTIME, **(runtime_config.value_json or {})}

    def mark_queued(self, db: Session, trigger: str) -> None:
        schedule_config, runtime_config = self.ensure_configs(db)
        schedule = {**DEFAULT_SCHEDULE, **(schedule_config.value_json or {})}
        now_iso = datetime.now(timezone.utc).isoformat()
        next_run_at = (datetime.now(timezone.utc) + timedelta(hours=int(schedule["interval_hours"]))).isoformat()
        runtime_config.value_json = {
            **DEFAULT_RUNTIME,
            **(runtime_config.value_json or {}),
            "status": "QUEUED",
            "last_trigger": trigger,
            "last_message": f"Đã xếp hàng lượt làm mới corpus từ trigger `{trigger}`.",
            "last_started_at": runtime_config.value_json.get("last_started_at") if runtime_config.value_json else None,
            "queued_at": now_iso,
            "next_run_at": next_run_at,
        }
        db.commit()

    def should_queue_periodic_run(self, db: Session) -> bool:
        schedule = self.get_schedule(db)
        runtime = self.get_runtime(db)
        if not bool(schedule.get("enabled", True)):
            return False
        if runtime.get("status") in {"QUEUED", "RUNNING"}:
            return False

        next_run_raw = runtime.get("next_run_at")
        if next_run_raw:
            try:
                next_run_at = datetime.fromisoformat(str(next_run_raw))
                if next_run_at.tzinfo is None:
                    next_run_at = next_run_at.replace(tzinfo=timezone.utc)
                return next_run_at <= datetime.now(timezone.utc)
            except ValueError:
                pass

        last_success_raw = runtime.get("last_success_at")
        if not last_success_raw:
            return True

        try:
            last_success_at = datetime.fromisoformat(str(last_success_raw))
            if last_success_at.tzinfo is None:
                last_success_at = last_success_at.replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        due_at = last_success_at + timedelta(hours=int(schedule["interval_hours"]))
        return due_at <= datetime.now(timezone.utc)

    async def run_refresh(self, db: Session, trigger: str = "manual") -> dict:
        schedule_config, runtime_config = self.ensure_configs(db)
        schedule = {**DEFAULT_SCHEDULE, **(schedule_config.value_json or {})}
        now = datetime.now(timezone.utc)

        runtime_config.value_json = {
            **DEFAULT_RUNTIME,
            **(runtime_config.value_json or {}),
            "status": "RUNNING",
            "last_trigger": trigger,
            "last_started_at": now.isoformat(),
            "last_message": f"Đang làm mới corpus từ trigger `{trigger}`.",
        }
        db.commit()

        try:
            enabled_domains = {
                item.domain
                for item in db.query(DataSource).filter(DataSource.is_enabled.is_(True)).all()
                if item.domain
            }
            corpus_result = await collect_training_corpus(
                target_documents=int(schedule["target_documents"]),
                allowed_domains=enabled_domains or None,
            )
            import_result = await import_snapshot_records(db)
            finished_at = datetime.now(timezone.utc)
            next_run_at = finished_at + timedelta(hours=int(schedule["interval_hours"]))
            result = {
                "corpus": corpus_result,
                "import": import_result,
                "finished_at": finished_at.isoformat(),
            }
            runtime_config.value_json = {
                **DEFAULT_RUNTIME,
                **(runtime_config.value_json or {}),
                "status": "READY",
                "last_trigger": trigger,
                "last_completed_at": finished_at.isoformat(),
                "last_success_at": finished_at.isoformat(),
                "last_message": f"Đã làm mới corpus thành công qua trigger `{trigger}`.",
                "next_run_at": next_run_at.isoformat(),
                "last_result": result,
            }
            db.commit()
            self._notify_admins(db, "Studify đã làm mới corpus", "Corpus UIT đã được cập nhật và re-index thành công.")
            return result
        except Exception as exc:
            failed_at = datetime.now(timezone.utc)
            retry_after = failed_at + timedelta(hours=int(schedule["retry_after_hours_on_failure"]))
            runtime_config.value_json = {
                **DEFAULT_RUNTIME,
                **(runtime_config.value_json or {}),
                "status": "FAILED",
                "last_trigger": trigger,
                "last_completed_at": failed_at.isoformat(),
                "last_message": str(exc),
                "next_run_at": retry_after.isoformat(),
                "last_result": {"error": str(exc)},
            }
            db.commit()
            self._notify_admins(db, "Studify chưa làm mới corpus thành công", str(exc))
            raise

    def _notify_admins(self, db: Session, title: str, content: str) -> None:
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        for admin in admins:
            db.add(
                InAppNotification(
                    user_id=admin.id,
                    title=title,
                    content=content,
                    action_link="/admin",
                )
            )
        db.commit()
