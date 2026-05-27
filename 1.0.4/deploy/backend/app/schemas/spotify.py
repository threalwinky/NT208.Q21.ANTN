from __future__ import annotations

from pydantic import BaseModel


class SpotifyStatusOut(BaseModel):
    enabled: bool
    connected: bool
    spotify_user_id: str | None = None
    display_name: str | None = None
    scopes: list[str] = []
    uses_curated_fallback: bool


class SpotifyConnectPreviewRequest(BaseModel):
    spotify_user_id: str | None = None
    display_name: str | None = None
    access_token_preview: str | None = None
    scopes: list[str] = []


class SpotifyPlaylistItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    image_url: str | None = None
    tracks_total: int = 0
    external_url: str | None = None
    embed_url: str | None = None


class PlaylistMappingRequest(BaseModel):
    spotify_playlist_id: str
    theme: str


class PlaylistMappingOut(BaseModel):
    id: int
    spotify_playlist_id: str
    theme: str
    title: str
