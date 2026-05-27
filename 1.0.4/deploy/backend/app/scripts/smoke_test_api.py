from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test Studify API and frontend routes.")
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1")
    parser.add_argument("--frontend-base", default="http://localhost:3000")
    return parser.parse_args()


async def request(client: httpx.AsyncClient, method: str, path: str, **kwargs: Any) -> httpx.Response:
    response = await client.request(method, path, **kwargs)
    response.raise_for_status()
    return response


async def login(api_base: str, username: str, password: str) -> tuple[httpx.AsyncClient, dict]:
    client = httpx.AsyncClient(base_url=api_base, timeout=40.0)
    response = await request(client, "POST", "/auth/login", json={"username": username, "password": password})
    payload = response.json()
    client.headers["Authorization"] = f"Bearer {payload['access_token']}"
    return client, payload


async def stream_chat(client: httpx.AsyncClient, content: str, session_id: int | None = None) -> dict:
    final_event: dict[str, Any] | None = None
    async with client.stream(
        "POST",
        "/chat/stream",
        json={"content": content, "session_id": session_id},
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line.removeprefix("data:").strip()
            if not payload:
                continue
            event = json.loads(payload)
            if event.get("type") == "done":
                final_event = event
    if final_event is None:
        raise RuntimeError("Stream chat did not produce a final event.")
    return final_event


async def test_frontend(frontend_base: str) -> list[str]:
    checked_paths = ["/", "/login", "/assistant", "/dashboard", "/academic", "/planner", "/announcements", "/diary"]
    async with httpx.AsyncClient(base_url=frontend_base, timeout=30.0, follow_redirects=True) as client:
        for path in checked_paths:
            response = await client.get(path)
            response.raise_for_status()
    return checked_paths


async def main() -> None:
    args = parse_args()
    summary: dict[str, Any] = {"frontend_paths": [], "student": {}, "admin": {}}

    async with httpx.AsyncClient(base_url=args.api_base, timeout=30.0) as public_client:
        root_response = await public_client.get(args.api_base.removesuffix("/api/v1").rstrip("/"))
        root_response.raise_for_status()
        health_response = await request(public_client, "GET", "/health")
        summary["health"] = health_response.json()

    summary["frontend_paths"] = await test_frontend(args.frontend_base)

    student_client, student_login = await login(args.api_base, "24522045", "24522045")
    try:
        summary["student"]["login_user"] = student_login["user"]["username"]
        summary["student"]["me"] = (await request(student_client, "GET", "/auth/me")).json()
        summary["student"]["dashboard"] = (await request(student_client, "GET", "/dashboard/overview")).json()["metrics"]

        announcements = (await request(student_client, "GET", "/announcements")).json()
        summary["student"]["announcements"] = len(announcements)
        if announcements:
            await request(student_client, "POST", f"/announcements/{announcements[0]['id']}/save")

        documents = (await request(student_client, "GET", "/planner/documents")).json()
        events = (await request(student_client, "GET", "/planner/events")).json()
        class_schedule = (await request(student_client, "GET", "/planner/class-schedule")).json()
        exam_schedule = (await request(student_client, "GET", "/planner/exam-schedule")).json()
        tasks = (await request(student_client, "GET", "/planner/tasks")).json()
        summary["student"]["planner"] = {
            "documents": len(documents),
            "events": len(events),
            "class_schedule": len(class_schedule),
            "exam_schedule": len(exam_schedule),
            "tasks": len(tasks),
        }

        created_task = (
            await request(
                student_client,
                "POST",
                "/planner/tasks",
                json={
                    "title": "Smoke test task",
                    "description": "Task được tạo trong bước smoke test",
                    "task_type": "Kiểm thử",
                    "priority": "MEDIUM",
                    "due_at": "2026-04-12T10:00:00+07:00",
                    "is_recurring": False,
                },
            )
        ).json()
        summary["student"]["created_task_id"] = created_task["id"]
        await request(student_client, "PATCH", f"/planner/tasks/{created_task['id']}/complete")

        chat_reply = await stream_chat(
            student_client,
            "Hôm nay mình hơi áp lực vì deadline dồn, bạn giúp mình sắp lại tuần này với.",
        )
        summary["student"]["chat"] = {
            "session_id": chat_reply["session_id"],
            "category": chat_reply["category"],
            "citations": len(chat_reply["citations"]),
        }
        sessions = (await request(student_client, "GET", "/chat/sessions")).json()
        summary["student"]["chat_sessions"] = len(sessions)

        moods = (await request(student_client, "GET", "/diary/moods")).json()
        journals = (await request(student_client, "GET", "/diary/journals")).json()
        resources = (await request(student_client, "GET", "/diary/resources")).json()
        summary["student"]["diary"] = {
            "moods": len(moods),
            "journals": len(journals),
            "resources": len(resources),
        }
        if moods:
            await request(
                student_client,
                "POST",
                "/diary/checkin",
                json={
                    "mood_state_id": moods[0]["id"],
                    "short_note": "Smoke test check-in",
                    "energy_level": 3,
                    "needs_human_support": False,
                },
            )
    finally:
        await student_client.aclose()

    admin_client, admin_login = await login(args.api_base, "admin", "admin")
    try:
        summary["admin"]["login_user"] = admin_login["user"]["username"]
        summary["admin"]["overview"] = (await request(admin_client, "GET", "/admin/overview")).json()
        sources = (await request(admin_client, "GET", "/admin/sources")).json()
        logs = (await request(admin_client, "GET", "/admin/crawler-logs")).json()
        configs = (await request(admin_client, "GET", "/admin/configs")).json()
        summary["admin"]["sources"] = len(sources)
        summary["admin"]["logs"] = len(logs)
        summary["admin"]["configs"] = len(configs)
        await request(admin_client, "POST", "/admin/reindex")
        await request(admin_client, "POST", "/admin/knowledge-refresh")
        summary["admin"]["runtime"] = (await request(admin_client, "GET", "/admin/runtime")).json()
        if sources:
            await request(admin_client, "POST", f"/admin/sources/{sources[0]['id']}/crawl")
    finally:
        await admin_client.aclose()

    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
