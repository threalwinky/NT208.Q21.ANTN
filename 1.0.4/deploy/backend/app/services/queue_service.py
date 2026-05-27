from __future__ import annotations

import json

from redis import Redis

from app.core.config import get_settings


class QueueService:
    def __init__(self) -> None:
        settings = get_settings()
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.queue_name = "studify_jobs"

    def push_job(self, job_type: str, payload: dict) -> None:
        self.redis.rpush(self.queue_name, json.dumps({"job_type": job_type, "payload": payload}))

    def pop_job(self, timeout: int = 5) -> dict | None:
        result = self.redis.blpop(self.queue_name, timeout=timeout)
        if result is None:
            return None
        _, content = result
        return json.loads(content)

    def size(self) -> int:
        return int(self.redis.llen(self.queue_name))
