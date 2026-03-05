import asyncio
import logging

from shazamio import Shazam

logger = logging.getLogger(__name__)


class ShazamClient:
    def __init__(self):
        self._shazam = Shazam()

    async def recognize(self, audio_path: str) -> dict | None:
        """
        Recognize a track from a local audio file.
        Returns {"title": ..., "artist": ...} or None.
        """
        try:
            result = await self._shazam.recognize(audio_path)

            track = result.get("track")
            if not track:
                logger.info("Shazam: no track found")
                return None

            title  = track.get("title", "")
            artist = track.get("subtitle", "")   # Shazam puts artist in 'subtitle'

            if not title:
                return None

            logger.info(f"Shazam identified: {artist} — {title}")
            return {"title": title, "artist": artist}

        except Exception as e:
            logger.error(f"Shazam error: {e}")
            return None
