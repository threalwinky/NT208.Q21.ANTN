from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.knowledge import SupportResource
from app.models.users import User
from app.models.wellbeing import MoodJournal, MoodState
from app.schemas.wellbeing import (
    EnergyInsightOut,
    EnergyInsightPreviewRequest,
    MoodCheckinRequest,
    MoodJournalOut,
    MoodStateOut,
    SupportResourceOut,
)
from app.services.wellbeing_service import WellbeingService

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


@router.get("/journals", response_model=list[MoodJournalOut])
def list_journals(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[MoodJournalOut]:
    service = WellbeingService()
    items = (
        db.query(MoodJournal)
        .filter(MoodJournal.user_id == user.id, MoodJournal.is_soft_deleted.is_(False))
        .order_by(MoodJournal.created_at.desc())
        .limit(20)
        .all()
    )
    journals: list[MoodJournalOut] = []
    for item in items:
        energy_level, energy_label, energy_summary, signals = service.serialize_journal(item)
        journals.append(
            MoodJournalOut(
                id=item.id,
                short_note=item.short_note,
                energy_level=energy_level,
                energy_label=energy_label,
                energy_summary=energy_summary,
                signals=signals,
                needs_human_support=item.needs_human_support,
                created_at=item.created_at,
                mood_label=item.mood_state.display_name if item.mood_state else None,
            )
        )
    return journals


@router.post("/checkin", response_model=MoodJournalOut)
def create_checkin(
    payload: MoodCheckinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MoodJournalOut:
    service = WellbeingService()
    mood_state = db.query(MoodState).filter(MoodState.id == payload.mood_state_id).first() if payload.mood_state_id else None
    analysis = service.analyze_energy(mood_state, payload.short_note)
    journal = MoodJournal(
        user_id=user.id,
        mood_state_id=payload.mood_state_id,
        short_note=payload.short_note,
        energy_level=analysis.level,
        needs_human_support=payload.needs_human_support,
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return MoodJournalOut(
        id=journal.id,
        short_note=journal.short_note,
        energy_level=analysis.level,
        energy_label=analysis.label,
        energy_summary=analysis.summary,
        signals=analysis.signals,
        needs_human_support=journal.needs_human_support,
        created_at=journal.created_at,
        mood_label=journal.mood_state.display_name if journal.mood_state else None,
    )


@router.get("/insight", response_model=EnergyInsightOut)
async def get_insight(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EnergyInsightOut:
    insight = await WellbeingService().build_insight(db, user)
    return serialize_insight(insight)


@router.post("/insight-preview", response_model=EnergyInsightOut)
async def preview_insight(
    payload: EnergyInsightPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnergyInsightOut:
    insight = await WellbeingService().build_preview_insight(
        db,
        user,
        mood_state_id=payload.mood_state_id,
        short_note=payload.short_note,
    )
    return serialize_insight(insight)


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
