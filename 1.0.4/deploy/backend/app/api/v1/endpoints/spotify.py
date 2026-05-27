from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.users import User
from app.models.wellbeing import MusicPlaylist, SpotifyAccount, SpotifyPlaylistMapping
from app.schemas.spotify import (
    PlaylistMappingOut,
    PlaylistMappingRequest,
    SpotifyConnectPreviewRequest,
    SpotifyPlaylistItem,
    SpotifyStatusOut,
)

router = APIRouter()

_SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SPOTIFY_API_BASE = "https://api.spotify.com/v1"
_OAUTH_SCOPES = "playlist-read-private playlist-read-collaborative user-read-private"
_STATE_ALGO = "HS256"
_STATE_TTL_SECONDS = 600


def _account_for(db: Session, user: User) -> SpotifyAccount | None:
    return db.query(SpotifyAccount).filter(SpotifyAccount.user_id == user.id).first()


def _serialize_status(account: SpotifyAccount | None) -> SpotifyStatusOut:
    settings = get_settings()
    return SpotifyStatusOut(
        enabled=settings.spotify_is_enabled,
        connected=bool(account and account.is_connected),
        spotify_user_id=account.spotify_user_id if account else None,
        display_name=account.display_name if account else None,
        scopes=account.scopes or [] if account else [],
        uses_curated_fallback=not settings.spotify_is_enabled,
    )


def _fernet_key(settings) -> bytes:
    raw_key = settings.spotify_token_encryption_key
    if raw_key:
        try:
            raw = base64.urlsafe_b64decode(raw_key.encode() + b"==")
            if len(raw) == 32:
                return base64.urlsafe_b64encode(raw)
        except Exception:
            pass
    # Derive a 32-byte key from SECRET_KEY so it's always available
    derived = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(derived)


def _encrypt(text: str, settings) -> str:
    from cryptography.fernet import Fernet
    return Fernet(_fernet_key(settings)).encrypt(text.encode()).decode()


def _decrypt(ciphertext: str, settings) -> str:
    from cryptography.fernet import Fernet, InvalidToken
    try:
        return Fernet(_fernet_key(settings)).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Không giải mã được token Spotify.") from exc


def _make_state(user_id: int, settings) -> str:
    payload = {
        "sub": str(user_id),
        "nonce": secrets.token_hex(16),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_STATE_ALGO)


def _verify_state(state: str, settings) -> int:
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[_STATE_ALGO])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="State OAuth không hợp lệ hoặc đã hết hạn.") from exc


async def _exchange_code(code: str, settings) -> dict:
    credentials = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Lấy token từ Spotify thất bại.")
    return resp.json()


async def _refresh_access_token(refresh_token: str, settings) -> dict:
    credentials = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Làm mới token Spotify thất bại.")
    return resp.json()


async def _get_valid_access_token(account: SpotifyAccount, db: Session, settings) -> str:
    if not account.is_connected or not account.access_token_enc:
        raise HTTPException(status_code=403, detail="Tài khoản Spotify chưa kết nối.")

    now = datetime.now(timezone.utc)
    expires_at = account.token_expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at is None or now >= expires_at - timedelta(seconds=60):
        if not account.refresh_token_enc:
            raise HTTPException(status_code=403, detail="Không có refresh token, vui lòng kết nối lại Spotify.")
        refresh_token = _decrypt(account.refresh_token_enc, settings)
        token_data = await _refresh_access_token(refresh_token, settings)
        access_token = token_data["access_token"]
        account.access_token_enc = _encrypt(access_token, settings)
        if "refresh_token" in token_data:
            account.refresh_token_enc = _encrypt(token_data["refresh_token"], settings)
        account.access_token_preview = access_token[:40]
        account.token_expires_at = now + timedelta(seconds=token_data.get("expires_in", 3600))
        db.commit()
        return access_token

    return _decrypt(account.access_token_enc, settings)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status", response_model=SpotifyStatusOut)
def spotify_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SpotifyStatusOut:
    return _serialize_status(_account_for(db, user))


@router.get("/connect")
def spotify_connect(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> RedirectResponse:
    settings = get_settings()
    if not settings.spotify_is_enabled:
        raise HTTPException(status_code=503, detail="Tính năng Spotify chưa được bật.")
    state = _make_state(user.id, settings)
    params = urlencode({
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "state": state,
        "scope": _OAUTH_SCOPES,
        "show_dialog": "false",
    })
    return RedirectResponse(url=f"{_SPOTIFY_AUTH_URL}?{params}")


@router.get("/callback")
async def spotify_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify trả về lỗi: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Thiếu code hoặc state từ Spotify.")

    user_id = _verify_state(state, settings)
    token_data = await _exchange_code(code, settings)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "").split()

    # Fetch Spotify user profile
    spotify_user_id: str | None = None
    display_name: str | None = None
    try:
        async with httpx.AsyncClient() as client:
            profile_resp = await client.get(
                f"{_SPOTIFY_API_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=8,
            )
        if profile_resp.status_code == 200:
            profile = profile_resp.json()
            spotify_user_id = profile.get("id")
            display_name = profile.get("display_name")
    except Exception:
        pass

    account = db.query(SpotifyAccount).filter(SpotifyAccount.user_id == user_id).first()
    if account is None:
        account = SpotifyAccount(user_id=user_id)
        db.add(account)

    account.spotify_user_id = spotify_user_id
    account.display_name = display_name
    account.access_token_enc = _encrypt(access_token, settings)
    account.refresh_token_enc = _encrypt(refresh_token, settings) if refresh_token else None
    account.access_token_preview = access_token[:40]
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account.scopes = scopes
    account.is_connected = True
    db.commit()

    return {"connected": True, "display_name": display_name, "spotify_user_id": spotify_user_id}


@router.get("/playlists", response_model=list[SpotifyPlaylistItem])
async def list_user_playlists(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SpotifyPlaylistItem]:
    settings = get_settings()
    account = _account_for(db, user)
    if not account or not account.is_connected:
        raise HTTPException(status_code=403, detail="Chưa kết nối Spotify.")

    access_token = await _get_valid_access_token(account, db, settings)
    items: list[SpotifyPlaylistItem] = []

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_SPOTIFY_API_BASE}/me/playlists",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": 50},
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Không lấy được danh sách playlist từ Spotify.")

    for pl in resp.json().get("items", []):
        if not pl:
            continue
        images = pl.get("images") or []
        image_url = images[0]["url"] if images else None
        ext_urls = pl.get("external_urls") or {}
        spotify_url = ext_urls.get("spotify")
        embed_url = f"https://open.spotify.com/embed/playlist/{pl['id']}" if pl.get("id") else None
        items.append(
            SpotifyPlaylistItem(
                id=pl["id"],
                name=pl.get("name", ""),
                description=pl.get("description") or None,
                image_url=image_url,
                tracks_total=pl.get("tracks", {}).get("total", 0),
                external_url=spotify_url,
                embed_url=embed_url,
            )
        )
    return items


@router.post("/playlist-mappings", response_model=PlaylistMappingOut, status_code=201)
async def create_playlist_mapping(
    payload: PlaylistMappingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlaylistMappingOut:
    settings = get_settings()
    account = _account_for(db, user)
    if not account or not account.is_connected:
        raise HTTPException(status_code=403, detail="Chưa kết nối Spotify.")

    access_token = await _get_valid_access_token(account, db, settings)

    # Fetch playlist info from Spotify to get title
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_SPOTIFY_API_BASE}/playlists/{payload.spotify_playlist_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "id,name,description,images,external_urls"},
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Không lấy được thông tin playlist từ Spotify.")

    pl_data = resp.json()
    title = pl_data.get("name", payload.spotify_playlist_id)
    images = pl_data.get("images") or []
    cover_url = images[0]["url"] if images else None
    ext_urls = pl_data.get("external_urls") or {}
    spotify_url = ext_urls.get("spotify")
    embed_url = f"https://open.spotify.com/embed/playlist/{payload.spotify_playlist_id}"

    # Upsert MusicPlaylist record
    music_pl = db.query(MusicPlaylist).filter(
        MusicPlaylist.spotify_playlist_id == payload.spotify_playlist_id
    ).first() if hasattr(MusicPlaylist, "spotify_playlist_id") else None

    if music_pl is None:
        music_pl = MusicPlaylist(
            theme=payload.theme,
            title=title,
            spotify_url=spotify_url,
            embed_url=embed_url,
            cover_url=cover_url,
            is_active=True,
        )
        db.add(music_pl)
        db.flush()

    # Upsert SpotifyPlaylistMapping
    mapping = db.query(SpotifyPlaylistMapping).filter(
        SpotifyPlaylistMapping.playlist_id == music_pl.id,
        SpotifyPlaylistMapping.mood_code == payload.theme,
    ).first()
    if mapping is None:
        mapping = SpotifyPlaylistMapping(
            playlist_id=music_pl.id,
            mood_code=payload.theme,
            weight=1.0,
        )
        db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return PlaylistMappingOut(
        id=mapping.id,
        spotify_playlist_id=payload.spotify_playlist_id,
        theme=payload.theme,
        title=title,
    )


@router.post("/connect-preview", response_model=SpotifyStatusOut)
def connect_preview(
    payload: SpotifyConnectPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SpotifyStatusOut:
    account = _account_for(db, user)
    if account is None:
        account = SpotifyAccount(user_id=user.id)
        db.add(account)
    account.spotify_user_id = payload.spotify_user_id
    account.display_name = payload.display_name
    account.access_token_preview = (payload.access_token_preview or "")[:40] or None
    account.scopes = payload.scopes
    account.is_connected = True
    db.commit()
    db.refresh(account)
    return _serialize_status(account)


@router.post("/disconnect", response_model=SpotifyStatusOut)
def disconnect_spotify(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SpotifyStatusOut:
    account = _account_for(db, user)
    if account:
        account.is_connected = False
        account.access_token_enc = None
        account.refresh_token_enc = None
        account.access_token_preview = None
        account.token_expires_at = None
        db.commit()
        db.refresh(account)
    return _serialize_status(account)
