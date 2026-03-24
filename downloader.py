import asyncio
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import yt_dlp
from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)

PLATFORM_MAP = {
    "YouTube":      r"(youtube\.com/|youtu\.be/)",
    "TikTok":       r"(tiktok\.com|vm\.tiktok\.com)",
    "Instagram":    r"(instagram\.com|instagr\.am)",
    "VK":           r"vk\.com/(video|clip|wall)",
    "SoundCloud":   r"soundcloud\.com",
    "Spotify":      r"open\.spotify\.com",
    "Deezer":       r"deezer\.com",
    "Yandex Music": r"music\.yandex\.(ru|kz|com)",
    "Bandcamp":     r"bandcamp\.com",
    "OK.ru":        r"ok\.ru/video",
    "Twitter/X":    r"(twitter\.com|x\.com)/\w+/status",
    "Facebook":     r"facebook\.com.*(video|reel)",
    "Dailymotion":  r"dailymotion\.com",
    "Mixcloud":     r"mixcloud\.com",
}

# yt-dlp format selectors
AUDIO_FORMAT    = "bestaudio/best"
YTDLP_BASE_OPTS = {
    "quiet":       True,
    "no_warnings": True,
    "noprogress":  True,
}

# PO Token cache: {"po_token": ..., "visitor_data": ..., "expires": ...}
_pot_cache: dict = {}
_POT_TTL = 3600  # regenerate every hour

# Write cookies.txt from env var if not present
_COOKIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
_b64 = os.environ.get("COOKIES_B64", "")
print(f"[cookies] path={_COOKIES_PATH}, exists={os.path.exists(_COOKIES_PATH)}, COOKIES_B64={bool(_b64)}", flush=True)
if not os.path.exists(_COOKIES_PATH) and _b64:
    import base64
    with open(_COOKIES_PATH, "wb") as _f:
        _f.write(base64.b64decode(_b64.strip()))
    print("[cookies] cookies.txt written from COOKIES_B64")


def _get_po_token() -> dict:
    """Generate PO Token via youtube-po-token-generator (Node.js)."""
    global _pot_cache
    if _pot_cache and time.time() < _pot_cache.get("expires", 0):
        return _pot_cache
    try:
        result = subprocess.run(
            ["youtube-po-token-generator"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        _pot_cache = {
            "po_token":    data["poToken"],
            "visitor_data": data["visitorData"],
            "expires":     time.time() + _POT_TTL,
        }
        logger.info("PO Token refreshed")
    except Exception as e:
        logger.warning(f"PO Token generation failed: {e}")
        _pot_cache = {}
    return _pot_cache


def _yt_opts() -> dict:
    return {}


def _cookies_opts() -> dict:
    if os.path.exists(_COOKIES_PATH):
        return {"cookiefile": _COOKIES_PATH}
    return {}


class MusicDownloader:
    def __init__(self):
        self.ytmusic = YTMusic()

    # ─────────────────────────────────────────
    # Platform detection
    # ─────────────────────────────────────────

    def detect_platform(self, url: str) -> str:
        for name, pattern in PLATFORM_MAP.items():
            if re.search(pattern, url, re.IGNORECASE):
                return name
        return "Unknown"

    # ─────────────────────────────────────────
    # Download: raw audio (no conversion) — for Shazam
    # ─────────────────────────────────────────

    async def download_raw_audio(self, url: str, output_dir: str) -> str | None:
        opts = {
            **YTDLP_BASE_OPTS,
            **_yt_opts(),
            **_cookies_opts(),
            "format": AUDIO_FORMAT,
            "outtmpl": f"{output_dir}/raw.%(ext)s",
        }
        return await asyncio.to_thread(self._ydl_download, url, opts, output_dir)

    # ─────────────────────────────────────────
    # Download: convert to mp3 — final delivery
    # ─────────────────────────────────────────

    async def extract_audio(self, url: str, output_dir: str) -> str | None:
        opts = {
            **YTDLP_BASE_OPTS,
            **_yt_opts(),
            **_cookies_opts(),
            "format": AUDIO_FORMAT,
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
            "postprocessors": [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": "192",
            }],
        }
        return await asyncio.to_thread(self._ydl_download, url, opts, output_dir)

    # ─────────────────────────────────────────
    # Get metadata without downloading
    # ─────────────────────────────────────────

    async def get_meta(self, url: str) -> dict:
        opts = {**YTDLP_BASE_OPTS, **_yt_opts(), "skip_download": True}
        try:
            def _fetch():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False) or {}
            info = await asyncio.to_thread(_fetch)
            return {
                "title":  info.get("title", ""),
                "artist": info.get("artist") or info.get("uploader", ""),
            }
        except Exception:
            return {}

    # ─────────────────────────────────────────
    # Search (YouTube Music first, yt-dlp fallback)
    # ─────────────────────────────────────────

    async def search_track(self, query: str, limit: int = 8) -> list[dict]:
        results = await self._ytmusic_search(query, limit)
        if results:
            return results
        logger.warning("YTMusic search failed, falling back to yt-dlp")
        return await self._ytdlp_search(query, limit)

    async def _ytmusic_search(self, query: str, limit: int) -> list[dict]:
        try:
            raw = await asyncio.to_thread(
                self.ytmusic.search, query, filter="songs", limit=limit
            )
            tracks = []
            for item in raw:
                vid = item.get("videoId")
                if not vid:
                    continue
                artist = (item.get("artists") or [{}])[0].get("name", "Unknown")
                secs   = item.get("duration_seconds", 0) or 0
                tracks.append({
                    "id":       vid,
                    "title":    item.get("title", "Unknown"),
                    "artist":   artist,
                    "duration": _fmt_duration(secs),
                    "source":   "ytmusic",
                })
            return tracks
        except Exception as e:
            logger.error(f"YTMusic search error: {e}")
            return []

    async def _ytdlp_search(self, query: str, limit: int) -> list[dict]:
        opts = {**YTDLP_BASE_OPTS, "extract_flat": True}
        try:
            def _search():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            info    = await asyncio.to_thread(_search)
            entries = (info or {}).get("entries") or []
            return [
                {
                    "id":       e["id"],
                    "title":    e.get("title", "Unknown"),
                    "artist":   e.get("uploader", "Unknown"),
                    "duration": _fmt_duration(e.get("duration") or 0),
                    "source":   "youtube",
                }
                for e in entries if e.get("id")
            ]
        except Exception as e:
            logger.error(f"yt-dlp search error: {e}")
            return []

    # ─────────────────────────────────────────
    # Download by track dict (from search results)
    # ─────────────────────────────────────────

    async def download_by_id(self, track: dict, output_dir: str) -> str | None:
        url = f"https://www.youtube.com/watch?v={track['id']}"
        return await self.extract_audio(url, output_dir)

    # ─────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────

    @staticmethod
    def _ydl_download(url: str, opts: dict, output_dir: str) -> str | None:
        try:
            print(f"[ydl] cookiefile={opts.get('cookiefile')}, format={opts.get('format')}", flush=True)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            files = sorted(Path(output_dir).iterdir(), key=lambda f: f.stat().st_mtime)
            return str(files[-1]) if files else None
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None


def _fmt_duration(secs: int | float) -> str:
    secs = int(secs)
    if not secs:
        return ""
    return f"{secs // 60}:{secs % 60:02d}"
