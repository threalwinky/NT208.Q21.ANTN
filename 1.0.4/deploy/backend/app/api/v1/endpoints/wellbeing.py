from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.knowledge import SupportResource
from app.models.users import User
from app.models.wellbeing import MoodCheckin, MoodState, MusicPlaylist, WellbeingNote
from app.schemas.wellbeing import (
    EnergyInsightOut,
    EnergyInsightPreviewRequest,
    MoodStateOut,
    MusicPlaylistOut,
    MusicTrackOut,
    SupportResourceOut,
    WellbeingCheckinCreateRequest,
    WellbeingCheckinOut,
    WellbeingNoteCreateRequest,
    WellbeingNoteOut,
    WellbeingNoteUpdateRequest,
)
from app.services.wellbeing_service import WellbeingService

class MusicPlaylistRequest(BaseModel):
    theme: str
    title: str
    description: str | None = None
    spotify_url: str | None = None
    embed_url: str | None = None
    cover_url: str | None = None
    is_active: bool = True


class AiReflectOut(BaseModel):
    reflection: str
    suggestions: list[str] = []

router = APIRouter()


def serialize_insight(insight: dict) -> EnergyInsightOut:
    return EnergyInsightOut(
        latest_energy_level=insight["latest_energy_level"],
        latest_energy_label=insight["latest_energy_label"],
        latest_mood_label=insight["latest_mood_label"],
        average_energy_level=insight["average_energy_level"],
        trend=insight["trend"],
        summary=insight["summary"],
        signals=insight["signals"],
        low_energy_threshold=insight["low_energy_threshold"],
        recommendation_mode=insight["recommendation_mode"],
        recommendations=[
            {
                "kind": item.kind,
                "title": item.title,
                "subtitle": item.subtitle,
                "description": item.description,
                "url": item.url,
                "image_url": item.image_url,
            }
            for item in insight["recommendations"]
        ],
        music_theme=insight["music_theme"],
        music_theme_label=insight["music_theme_label"],
        music_tracks=[
            {
                "title": item.title,
                "artist": item.artist,
                "album": item.album,
                "url": item.url,
                "embed_url": item.embed_url,
                "image_url": item.image_url,
            }
            for item in insight["music_tracks"]
        ],
        energy_series=insight["energy_series"],
    )


def serialize_checkin(item: MoodCheckin) -> WellbeingCheckinOut:
    return WellbeingCheckinOut(
        id=item.id,
        mood_code=item.mood_code,
        valence=item.valence,
        energy=item.energy,
        stress=item.stress,
        motivation=item.motivation,
        focus=item.focus,
        sleep_quality=item.sleep_quality,
        note_preview=item.note_preview,
        needs_human_support=item.needs_human_support,
        safety_metadata=item.safety_metadata,
        created_at=item.created_at,
    )


def serialize_note(item: WellbeingNote) -> WellbeingNoteOut:
    return WellbeingNoteOut(
        id=item.id,
        title=item.title,
        content=item.content,
        mood_code=item.mood_code,
        is_private=item.is_private,
        needs_human_support=item.needs_human_support,
        safety_metadata=item.safety_metadata,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/moods", response_model=list[MoodStateOut])
def list_moods(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[MoodStateOut]:
    moods = db.query(MoodState).order_by(MoodState.intensity.asc()).all()
    return [
        MoodStateOut(
            id=item.id,
            code=item.code,
            display_name=item.display_name,
            description=item.description,
            color=item.color,
            intensity=item.intensity,
        )
        for item in moods
    ]


@router.get("/checkins", response_model=list[WellbeingCheckinOut])
def list_checkins(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[WellbeingCheckinOut]:
    items = db.query(MoodCheckin).filter(MoodCheckin.user_id == user.id).order_by(MoodCheckin.created_at.desc()).limit(30).all()
    return [serialize_checkin(item) for item in items]


@router.post("/checkins", response_model=WellbeingCheckinOut)
def create_checkin(
    payload: WellbeingCheckinCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WellbeingCheckinOut:
    note_preview = (payload.note_preview or "")[:255] or None
    item = MoodCheckin(
        user_id=user.id,
        mood_code=payload.mood_code,
        valence=payload.valence,
        energy=payload.energy,
        stress=payload.stress,
        motivation=payload.motivation,
        focus=payload.focus,
        sleep_quality=payload.sleep_quality,
        note_preview=note_preview,
        needs_human_support=payload.needs_human_support,
        safety_metadata=payload.safety_metadata,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_checkin(item)


@router.get("/insight", response_model=EnergyInsightOut)
async def get_insight(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EnergyInsightOut:
    return serialize_insight(await WellbeingService().build_insight(db, user))


@router.post("/insight-preview", response_model=EnergyInsightOut)
async def preview_insight(
    payload: EnergyInsightPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnergyInsightOut:
    insight = await WellbeingService().build_preview_insight(db, user, mood_state_id=payload.mood_state_id, short_note=payload.short_note)
    return serialize_insight(insight)


@router.get("/notes/export", response_model=list[WellbeingNoteOut])
def export_notes(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[WellbeingNoteOut]:
    items = db.query(WellbeingNote).filter(WellbeingNote.user_id == user.id, WellbeingNote.is_soft_deleted.is_(False)).order_by(WellbeingNote.created_at.asc()).all()
    return [serialize_note(item) for item in items]


@router.get("/notes", response_model=list[WellbeingNoteOut])
def list_notes(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[WellbeingNoteOut]:
    items = db.query(WellbeingNote).filter(WellbeingNote.user_id == user.id, WellbeingNote.is_soft_deleted.is_(False)).order_by(WellbeingNote.created_at.desc()).limit(40).all()
    return [serialize_note(item) for item in items]


@router.post("/notes", response_model=WellbeingNoteOut)
def create_note(
    payload: WellbeingNoteCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WellbeingNoteOut:
    item = WellbeingNote(
        user_id=user.id,
        title=payload.title.strip() or "Ghi chú riêng",
        content=payload.content,
        mood_code=payload.mood_code,
        needs_human_support=payload.needs_human_support,
        safety_metadata=payload.safety_metadata,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize_note(item)


@router.patch("/notes/{note_id}", response_model=WellbeingNoteOut)
def update_note(
    note_id: int,
    payload: WellbeingNoteUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WellbeingNoteOut:
    item = db.query(WellbeingNote).filter(WellbeingNote.id == note_id, WellbeingNote.user_id == user.id, WellbeingNote.is_soft_deleted.is_(False)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú.")
    if payload.title is not None:
        item.title = payload.title.strip() or "Ghi chú riêng"
    if payload.content is not None:
        item.content = payload.content
    if payload.mood_code is not None:
        item.mood_code = payload.mood_code
    if payload.needs_human_support is not None:
        item.needs_human_support = payload.needs_human_support
    if payload.safety_metadata is not None:
        item.safety_metadata = payload.safety_metadata
    db.commit()
    db.refresh(item)
    return serialize_note(item)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    item = db.query(WellbeingNote).filter(WellbeingNote.id == note_id, WellbeingNote.user_id == user.id, WellbeingNote.is_soft_deleted.is_(False)).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú.")
    item.is_soft_deleted = True
    db.commit()
    return {"deleted": True}


@router.get("/music", response_model=list[MusicTrackOut])
async def music_recommendations(
    theme: str = Query(default="focus"),
    limit: int = Query(default=6, ge=1, le=12),
    _: User = Depends(get_current_user),
) -> list[MusicTrackOut]:
    tracks = await WellbeingService().music_tracks(theme=theme, limit=limit)
    return [
        MusicTrackOut(title=item.title, artist=item.artist, album=item.album, url=item.url, embed_url=item.embed_url, image_url=item.image_url)
        for item in tracks
    ]


@router.get("/music/playlists", response_model=list[MusicPlaylistOut])
def curated_playlists(theme: str | None = Query(default=None), db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[MusicPlaylistOut]:
    query = db.query(MusicPlaylist).filter(MusicPlaylist.is_active.is_(True))
    if theme:
        query = query.filter(MusicPlaylist.theme == theme)
    items = query.order_by(MusicPlaylist.theme.asc(), MusicPlaylist.title.asc()).limit(30).all()
    return [
        MusicPlaylistOut(
            id=item.id,
            theme=item.theme,
            title=item.title,
            description=item.description,
            spotify_url=item.spotify_url,
            embed_url=item.embed_url,
            cover_url=item.cover_url,
            metadata_json=item.metadata_json,
        )
        for item in items
    ]


@router.get("/resources", response_model=list[SupportResourceOut])
def list_resources(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[SupportResourceOut]:
    items = db.query(SupportResource).order_by(SupportResource.urgent_priority.desc()).all()
    return [
        SupportResourceOut(
            id=item.id,
            title=item.title,
            description=item.description,
            resource_type=item.resource_type,
            owner_unit=item.owner_unit,
            link_url=item.link_url,
            contact=item.contact,
            is_official_uit=item.is_official_uit,
            urgent_priority=item.urgent_priority,
        )
        for item in items
    ]


# ── Wellbeing dashboard ───────────────────────────────────────────────────────

@router.get("/dashboard")
async def wellbeing_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    recent_checkins = (
        db.query(MoodCheckin)
        .filter(MoodCheckin.user_id == user.id)
        .order_by(MoodCheckin.created_at.desc())
        .limit(7)
        .all()
    )
    recent_notes_count = db.query(WellbeingNote).filter(
        WellbeingNote.user_id == user.id,
        WellbeingNote.is_soft_deleted.is_(False),
    ).count()

    avg_energy = 0.0
    avg_stress = 0.0
    avg_motivation = 0.0
    latest_mood = None
    if recent_checkins:
        avg_energy = sum(c.energy for c in recent_checkins) / len(recent_checkins)
        avg_stress = sum(c.stress for c in recent_checkins) / len(recent_checkins)
        avg_motivation = sum(c.motivation for c in recent_checkins) / len(recent_checkins)
        latest_mood = recent_checkins[0].mood_code

    return {
        "latest_mood": latest_mood,
        "avg_energy_7d": round(avg_energy, 1),
        "avg_stress_7d": round(avg_stress, 1),
        "avg_motivation_7d": round(avg_motivation, 1),
        "checkin_count_7d": len(recent_checkins),
        "notes_count": recent_notes_count,
        "checkins": [serialize_checkin(c) for c in recent_checkins[:3]],
    }


# ── Mood deletion ─────────────────────────────────────────────────────────────

@router.delete("/checkins/{checkin_id}")
def delete_checkin(checkin_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    item = db.query(MoodCheckin).filter(MoodCheckin.id == checkin_id, MoodCheckin.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy check-in.")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@router.delete("/checkins")
def delete_all_checkins(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    deleted = db.query(MoodCheckin).filter(MoodCheckin.user_id == user.id).delete()
    db.commit()
    return {"deleted": deleted}


# ── AI note reflection ────────────────────────────────────────────────────────

@router.post("/notes/{note_id}/ai-reflect", response_model=AiReflectOut)
async def ai_reflect_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiReflectOut:
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.enable_ai_note_reflection:
        raise HTTPException(status_code=403, detail="Tính năng AI phản chiếu ghi chú chưa được bật.")

    item = db.query(WellbeingNote).filter(
        WellbeingNote.id == note_id,
        WellbeingNote.user_id == user.id,
        WellbeingNote.is_soft_deleted.is_(False),
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú.")

    from app.services.llm import get_llm_provider
    llm = get_llm_provider()
    system_prompt = (
        "Bạn là Studify — trợ lý đồng hành sinh viên UIT. "
        "Sinh viên chia sẻ một ghi chú riêng tư. "
        "Hãy phản hồi ngắn gọn, ấm áp, hỗ trợ. "
        "Đừng chẩn đoán bệnh, đừng sử dụng thuật ngữ y khoa. "
        "Đề xuất 1-3 bước nhỏ cụ thể, thực tế mà sinh viên có thể thử ngay hôm nay. "
        "Phản hồi bằng JSON: {\"reflection\": \"...\", \"suggestions\": [\"...\", \"...\"]}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Ghi chú: {item.content[:800]}"},
    ]
    try:
        raw = await llm.chat(messages)
        import json as json_mod
        data = json_mod.loads(raw)
        return AiReflectOut(reflection=data.get("reflection", raw), suggestions=data.get("suggestions", []))
    except Exception:
        return AiReflectOut(
            reflection="Cảm ơn bạn đã chia sẻ. Hãy nhớ rằng bạn không phải đối mặt một mình — mỗi bước nhỏ đều có giá trị.",
            suggestions=["Uống một ly nước", "Hít thở sâu 3 lần", "Nghỉ ngơi 10 phút trước khi tiếp tục"],
        )


# ── Music playlist admin CRUD ─────────────────────────────────────────────────

@router.post("/music/playlists", response_model=MusicPlaylistOut)
def create_playlist(
    payload: MusicPlaylistRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> MusicPlaylistOut:
    item = MusicPlaylist(
        theme=payload.theme,
        title=payload.title,
        description=payload.description,
        spotify_url=payload.spotify_url,
        embed_url=payload.embed_url,
        cover_url=payload.cover_url,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return MusicPlaylistOut(
        id=item.id, theme=item.theme, title=item.title, description=item.description,
        spotify_url=item.spotify_url, embed_url=item.embed_url, cover_url=item.cover_url, metadata_json=item.metadata_json,
    )


@router.put("/music/playlists/{playlist_id}", response_model=MusicPlaylistOut)
def update_playlist(
    playlist_id: int,
    payload: MusicPlaylistRequest,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> MusicPlaylistOut:
    item = db.query(MusicPlaylist).filter(MusicPlaylist.id == playlist_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy playlist.")
    item.theme = payload.theme
    item.title = payload.title
    item.description = payload.description
    item.spotify_url = payload.spotify_url
    item.embed_url = payload.embed_url
    item.cover_url = payload.cover_url
    item.is_active = payload.is_active
    db.commit()
    db.refresh(item)
    return MusicPlaylistOut(
        id=item.id, theme=item.theme, title=item.title, description=item.description,
        spotify_url=item.spotify_url, embed_url=item.embed_url, cover_url=item.cover_url, metadata_json=item.metadata_json,
    )


@router.delete("/music/playlists/{playlist_id}")
def delete_playlist(playlist_id: int, db: Session = Depends(get_db), _=Depends(require_admin)) -> dict:
    item = db.query(MusicPlaylist).filter(MusicPlaylist.id == playlist_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy playlist.")
    db.delete(item)
    db.commit()
    return {"deleted": True}
