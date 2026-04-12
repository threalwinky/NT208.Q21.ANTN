from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random
from typing import Any, ClassVar

import httpx

from app.core.config import get_settings


@dataclass
class SpotifyTrack:
    track_id: str
    title: str
    artist: str
    album: str
    url: str
    embed_url: str
    image_url: str | None = None


class SpotifyService:
    _token_cache: ClassVar[str | None] = None
    _token_expires_at: ClassVar[datetime | None] = None
    _recent_track_ids: ClassVar[list[str]] = []

    def __init__(self) -> None:
        self.settings = get_settings()
        self.theme_queries = {
            "calm": [
                "lofi beats",
                "ambient chill",
                "gentle piano",
                "soft indie",
                "late night mellow",
                "rainy day acoustic",
                "dream pop calm",
            ],
            "focus": [
                "deep focus",
                "instrumental study",
                "productive beats",
                "coding mode",
                "jazzhop",
                "lofi study",
                "reading soundtrack",
            ],
            "upbeat": [
                "dance pop",
                "edm hits",
                "feel good pop",
                "happy hits",
                "party starter",
                "electro pop",
                "running pop mix",
            ],
            "love": [
                "love songs",
                "romantic pop",
                "acoustic love",
                "r&b love",
                "date night",
                "soft love songs",
                "late night romance",
            ],
        }
        self.fallback_catalog: dict[str, list[dict[str, str | None]]] = {
            "calm": [
                {
                    "title": "Soft Spot",
                    "artist": "keshi",
                    "album": "Requiem",
                    "track_id": "2aL4lMGhWdPpyPL6COPou7",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273617997bc09bb7fa23624eff5",
                },
                {
                    "title": "23:40",
                    "artist": "Hào",
                    "album": "23:40",
                    "track_id": "6qyK9SquQSHvNzrGHEUYNV",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b27303a6a68745b3cbecf690cc67",
                },
                {
                    "title": "Here With Me",
                    "artist": "d4vd",
                    "album": "Petals to Thorns",
                    "track_id": "0NLm9bQG7ikL5k9x9TtYT7",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273e5ff1941799cd30cb2aa072b",
                },
                {
                    "title": "Snooze",
                    "artist": "SZA",
                    "album": "SOS",
                    "track_id": "4iZ4pt7kvcaH6Yo8UoZ4s2",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273bc18bdade69ec5ef0bb25b17",
                },
                {
                    "title": "Daylight",
                    "artist": "David Kushner",
                    "album": "The Dichotomy",
                    "track_id": "5OGZ2Mx4Cs6RCndDRycGBJ",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273d010d5f2882bad368ee24403",
                },
                {
                    "title": "Softly",
                    "artist": "Clairo",
                    "album": "Immunity",
                    "track_id": "3r8b29rWOWwvxVyq3bSr1I",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b27378d601a8e07bef8b1f8ecf82",
                },
                {
                    "title": "Get You The Moon (feat. Snøw)",
                    "artist": "Kina, Snøw",
                    "album": "Get You The Moon (feat. Snøw)",
                    "track_id": "4ZLzoOkj0MPWrTLvooIuaa",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273121a9af58f3604f78dd68f6b",
                },
                {
                    "title": "golden hour",
                    "artist": "JVKE",
                    "album": "this is what ____ feels like (Vol. 1-4)",
                    "track_id": "5odlY52u43F5BjByhxg7wg",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273c2504e80ba2f258697ab2954",
                },
            ],
            "focus": [
                {
                    "title": "Nuvole Bianche",
                    "artist": "Ludovico Einaudi",
                    "album": "Una Mattina",
                    "track_id": "3weNRklVDqb4Rr5MhKBR3D",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2734ea8c5801bfdf5ac90719400",
                },
                {
                    "title": "Snowman",
                    "artist": "WYS",
                    "album": "1 Am. Study Session",
                    "track_id": "5oKzIi5OFGRD8f2oGaHLtj",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273455d8d81ba8ccd8a7b8970e1",
                },
                {
                    "title": "Sunflower",
                    "artist": "Rex Orange County",
                    "album": "Sunflower",
                    "track_id": "7h2nmmoWDi2UpfYKLKWLYB",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273e89fffbc825d52c018a2357e",
                },
                {
                    "title": "Glue Song",
                    "artist": "beabadoobee",
                    "album": "Glue Song",
                    "track_id": "3iBgrkexCzVuPy4O9vx7Mf",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273e3862aeefcb2f0860ef017e4",
                },
                {
                    "title": "Paris in the Rain",
                    "artist": "Lauv",
                    "album": "I met you when I was 18. (the playlist)",
                    "track_id": "2WdAV1VqmllcEznKlVOFxG",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2739ed5fcf212f05d55b1e61eae",
                },
                {
                    "title": "Coffee Breath",
                    "artist": "Flicka Roe",
                    "album": "Coffee Breath",
                    "track_id": "4jsVLYWHeoEt8UxxFWrWCH",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273b2d8dda987f48d61021ebb5d",
                },
                {
                    "title": "Warm on a Cold Night",
                    "artist": "HONNE",
                    "album": "Warm on a Cold Night (Deluxe)",
                    "track_id": "6Dg2RJihNlbkLSmtXY3p5f",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b27398ba0f90dd1805629ce4c53e",
                },
                {
                    "title": "Until I Found You",
                    "artist": "Stephen Sanchez",
                    "album": "Easy On My Eyes",
                    "track_id": "6VhuP99TE6gYNQRJIlAWFD",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2739522042f86d0bb0d4e9e3783",
                },
            ],
            "upbeat": [
                {
                    "title": "Espresso",
                    "artist": "Sabrina Carpenter",
                    "album": "Short n' Sweet",
                    "track_id": "2HRqTpkrJO5ggZyyK6NPWz",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273fd8d7a8d96871e791cb1f626",
                },
                {
                    "title": "Please Please Please",
                    "artist": "Sabrina Carpenter",
                    "album": "Short n' Sweet",
                    "track_id": "2tHwzyyOLoWSFqYNjeVMzj",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273fd8d7a8d96871e791cb1f626",
                },
                {
                    "title": "greedy",
                    "artist": "Tate McRae",
                    "album": "greedy",
                    "track_id": "3rUGC1vUpkDG9CZFHMur1t",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2735f677b5d3b81f08badd0775b",
                },
                {
                    "title": "Houdini",
                    "artist": "Dua Lipa",
                    "album": "Radical Optimism",
                    "track_id": "6D8y7Bck8h11byRY88Pt2z",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2732f8790ed72296c2614607575",
                },
                {
                    "title": "Beautiful Things",
                    "artist": "Benson Boone",
                    "album": "Fireworks & Rollerblades",
                    "track_id": "3xkHsmpQCBMytMJNiDf3Ii",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273831949037a1db10b87b005fa",
                },
                {
                    "title": "Vui Đét",
                    "artist": "CoolKid, RHYDER, BAN, Duy B, Trix",
                    "album": "Vui Đét",
                    "track_id": "5e1kUuII1bqgwu8fjuFNxE",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273ae5db36c8e3d5d2fdf08d611",
                },
                {
                    "title": "Superdam",
                    "artist": "DJ Long Nhat, Jay Trần",
                    "album": "Superdam",
                    "track_id": "4OcplIQEpR2i24WBXH9KDl",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273fba27de217201af27eb17eec",
                },
                {
                    "title": "Water",
                    "artist": "Tyla",
                    "album": "Water",
                    "track_id": "5aIVCx5tnk0ntmdiinnYvw",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273d20231861e86a6f74ef2393e",
                },
                {
                    "title": "Paint The Town Red",
                    "artist": "Doja Cat",
                    "album": "Paint The Town Red",
                    "track_id": "2IGMVunIBsBLtEQyoI1Mu7",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273e69a141e4ffe839c38c4c228",
                },
                {
                    "title": "Mất Kết Nối",
                    "artist": "Dương Domic",
                    "album": "Dữ Liệu Quý",
                    "track_id": "3CmacJj7VC4W6daC8BWd0h",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273aa8b2071efbaa7ec3f41b60b",
                },
            ],
            "love": [
                {
                    "title": "Until I Found You",
                    "artist": "Stephen Sanchez",
                    "album": "Easy On My Eyes",
                    "track_id": "6VhuP99TE6gYNQRJIlAWFD",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2739522042f86d0bb0d4e9e3783",
                },
                {
                    "title": "I Like Me Better",
                    "artist": "Lauv",
                    "album": "I met you when I was 18. (the playlist)",
                    "track_id": "4MagTPnkPiDuIa4P8GtW1b",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2739ed5fcf212f05d55b1e61eae",
                },
                {
                    "title": "Die With A Smile",
                    "artist": "Lady Gaga, Bruno Mars",
                    "album": "Die With A Smile",
                    "track_id": "2plbrEY59IikOBgBGLjaoe",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b27382ea2e9e1858aa012c57cd45",
                },
                {
                    "title": "Yellow",
                    "artist": "Coldplay",
                    "album": "Parachutes",
                    "track_id": "3AJwUDP919kvQ9QcozQPxg",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b2739164bafe9aaa168d93f4816a",
                },
                {
                    "title": "Perfect",
                    "artist": "Ed Sheeran",
                    "album": "÷ (Deluxe)",
                    "track_id": "0tgVpDi06FyKpA1z0VMD4v",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273ba5db46f4b838ef6027e6f96",
                },
                {
                    "title": "Lover",
                    "artist": "Taylor Swift",
                    "album": "Lover",
                    "track_id": "1dGr1c8CrMLDpV6mPbImSI",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273e787cffec20aa2a396a61647",
                },
                {
                    "title": "Snooze",
                    "artist": "SZA",
                    "album": "SOS",
                    "track_id": "4iZ4pt7kvcaH6Yo8UoZ4s2",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273bc18bdade69ec5ef0bb25b17",
                },
                {
                    "title": "Soft Spot",
                    "artist": "keshi",
                    "album": "Requiem",
                    "track_id": "2aL4lMGhWdPpyPL6COPou7",
                    "image_url": "https://i.scdn.co/image/ab67616d0000b273617997bc09bb7fa23624eff5",
                },
            ],
        }

    def _normalize_theme(self, theme: str) -> str:
        return theme if theme in self.theme_queries else "focus"

    def _reset_token_cache(self) -> None:
        self.__class__._token_cache = None
        self.__class__._token_expires_at = None

    async def _client_credentials_token(self) -> str | None:
        if not self.settings.spotify_client_id or not self.settings.spotify_client_secret:
            return None

        now = datetime.now(timezone.utc)
        if self.__class__._token_cache and self.__class__._token_expires_at and now < self.__class__._token_expires_at:
            return self.__class__._token_cache

        basic_token = base64.b64encode(
            f"{self.settings.spotify_client_id}:{self.settings.spotify_client_secret}".encode("utf-8")
        ).decode("utf-8")

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://accounts.spotify.com/api/token",
                    headers={
                        "Authorization": f"Basic {basic_token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "client_credentials"},
                )
        except httpx.HTTPError:
            return None

        if response.status_code >= 400:
            return None

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        if not access_token:
            return None

        self.__class__._token_cache = access_token
        self.__class__._token_expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return access_token

    async def _spotify_token(self) -> str | None:
        if self.settings.spotify_client_id and self.settings.spotify_client_secret:
            token = await self._client_credentials_token()
            if token:
                return token
        if self.settings.spotify_access_token:
            return self.settings.spotify_access_token
        return None

    def _collect_spotify_track(self, item: dict[str, Any]) -> SpotifyTrack | None:
        if not item:
            return None

        track_id = item.get("id")
        url = item.get("external_urls", {}).get("spotify")
        if not track_id or not url:
            return None

        artists = item.get("artists") or []
        album = item.get("album") or {}
        images = album.get("images") or []
        return SpotifyTrack(
            track_id=track_id,
            title=item.get("name", "Bài hát gợi ý"),
            artist=", ".join(artist.get("name", "") for artist in artists if artist.get("name")) or "Spotify",
            album=album.get("name", "Spotify"),
            url=url,
            embed_url=f"https://open.spotify.com/embed/track/{track_id}?utm_source=generator",
            image_url=images[0]["url"] if images else None,
        )

    def _rotate_recent_tracks(self, tracks: list[SpotifyTrack], limit: int) -> list[SpotifyTrack]:
        if not tracks:
            return []

        recent_ids = set(self.__class__._recent_track_ids[-18:])
        fresh_tracks = [track for track in tracks if track.track_id not in recent_ids]
        remaining_tracks = [track for track in tracks if track.track_id not in {item.track_id for item in fresh_tracks}]
        random.shuffle(fresh_tracks)
        random.shuffle(remaining_tracks)
        selected = (fresh_tracks + remaining_tracks)[:limit]
        if selected:
            self.__class__._recent_track_ids.extend(track.track_id for track in selected)
            self.__class__._recent_track_ids = self.__class__._recent_track_ids[-36:]
        return selected

    async def _search_query(
        self,
        client: httpx.AsyncClient,
        token: str,
        query: str,
        limit: int,
    ) -> tuple[str, list[dict[str, Any]]]:
        try:
            response = await client.get(
                "https://api.spotify.com/v1/search",
                params={"q": query, "type": "track", "limit": limit, "market": "VN"},
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError:
            return "error", []

        if response.status_code in {401, 403}:
            return "unauthorized", []
        if response.status_code >= 400:
            return "error", []

        payload = response.json()
        items = payload.get("tracks", {}).get("items", [])
        return "ok", items if isinstance(items, list) else []

    def _search_spotify_tracks_sync(self, theme: str, limit: int, token: str) -> list[SpotifyTrack]:
        queries = list(self.theme_queries[self._normalize_theme(theme)])
        random.shuffle(queries)
        search_limit = max(12, limit * 4)
        collected: list[SpotifyTrack] = []
        seen_urls: set[str] = set()
        max_candidates = max(limit * 4, 12)

        with httpx.Client(timeout=20) as client:
            for query in queries:
                try:
                    response = client.get(
                        "https://api.spotify.com/v1/search",
                        params={"q": query, "type": "track", "limit": search_limit, "market": "VN"},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                except httpx.HTTPError:
                    continue

                if response.status_code in {401, 403}:
                    self._reset_token_cache()
                    return []
                if response.status_code >= 400:
                    continue

                items = response.json().get("tracks", {}).get("items", [])
                if not isinstance(items, list):
                    continue
                random.shuffle(items)
                for item in items:
                    track = self._collect_spotify_track(item)
                    if track is None or track.url in seen_urls:
                        continue
                    seen_urls.add(track.url)
                    collected.append(track)
                    if len(collected) >= max_candidates:
                        return self._rotate_recent_tracks(collected, limit)

        return self._rotate_recent_tracks(collected, limit)

    def _fallback_tracks(self, theme: str, limit: int) -> list[SpotifyTrack]:
        catalog = list(self.fallback_catalog[self._normalize_theme(theme)])
        random.shuffle(catalog)
        tracks: list[SpotifyTrack] = []
        for item in catalog[:limit]:
            track_id = item["track_id"]
            if not track_id:
                continue
            tracks.append(
                SpotifyTrack(
                    track_id=track_id,
                    title=item["title"] or "Bài hát gợi ý",
                    artist=item["artist"] or "Spotify",
                    album=item["album"] or "Spotify",
                    url=f"https://open.spotify.com/track/{track_id}",
                    embed_url=f"https://open.spotify.com/embed/track/{track_id}?utm_source=generator",
                    image_url=item["image_url"],
                )
            )
        return self._rotate_recent_tracks(tracks, limit)

    async def search_tracks(self, theme: str = "focus", limit: int = 6) -> list[SpotifyTrack]:
        theme_key = self._normalize_theme(theme)
        limit = max(1, min(limit, 12))
        if not self.settings.spotify_enabled:
            return self._fallback_tracks(theme=theme_key, limit=limit)

        for attempt in range(2):
            token = await self._spotify_token()
            if not token:
                break

            tracks = await asyncio.to_thread(self._search_spotify_tracks_sync, theme_key, limit, token)
            if tracks:
                return tracks

            if attempt == 0:
                self._reset_token_cache()

        return self._fallback_tracks(theme=theme_key, limit=limit)
