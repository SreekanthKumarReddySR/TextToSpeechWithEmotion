from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts
import pyttsx3

from darwix_app.models import VoiceProfile


VOICE_OPTIONS = [
    {"id": "female_aria", "label": "Female - Aria", "gender": "female", "voice": "en-US-AriaNeural"},
    {"id": "female_jenny", "label": "Female - Jenny", "gender": "female", "voice": "en-US-JennyNeural"},
    {"id": "male_guy", "label": "Male - Guy", "gender": "male", "voice": "en-US-GuyNeural"},
    {"id": "male_davis", "label": "Male - Davis", "gender": "male", "voice": "en-US-DavisNeural"},
]


class TextToSpeechService:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def list_voices():
        return VOICE_OPTIONS

    @staticmethod
    def resolve_voice(voice_id: str | None, preferred_gender: str | None) -> dict:
        if voice_id:
            for option in VOICE_OPTIONS:
                if option["id"] == voice_id:
                    return option

        for option in VOICE_OPTIONS:
            if preferred_gender and option["gender"] == preferred_gender:
                return option

        return VOICE_OPTIONS[0]

    async def _save_edge(self, text: str, profile: VoiceProfile, output_path: Path):
        communicator = edge_tts.Communicate(
            text=text,
            voice=profile.voice_name,
            rate=profile.rate,
            volume=profile.volume,
            pitch=profile.pitch,
        )
        await communicator.save(str(output_path))

    def _save_local(self, text: str, profile: VoiceProfile, output_path: Path):
        speaker = pyttsx3.init()
        rate_value = 165
        if profile.rate.startswith("+"):
            rate_value += int(float(profile.rate[1:-1]) * 1.4)
        elif profile.rate.startswith("-"):
            rate_value -= int(float(profile.rate[1:-1]) * 1.4)

        volume_value = 0.85
        if profile.volume.startswith("+"):
            volume_value = min(1.0, 0.85 + float(profile.volume[1:-1]) / 100)
        elif profile.volume.startswith("-"):
            volume_value = max(0.4, 0.85 - float(profile.volume[1:-1]) / 100)

        speaker.setProperty("rate", rate_value)
        speaker.setProperty("volume", volume_value)
        speaker.save_to_file(text, str(output_path))
        speaker.runAndWait()
        speaker.stop()

    def synthesize(self, text: str, profile: VoiceProfile, filename_root: str) -> tuple[Path, str]:
        edge_path = self.output_dir / f"{filename_root}.mp3"
        try:
            asyncio.run(self._save_edge(text=text, profile=profile, output_path=edge_path))
            return edge_path, "edge-tts"
        except Exception:
            local_path = self.output_dir / f"{filename_root}.wav"
            self._save_local(text=text, profile=profile, output_path=local_path)
            return local_path, "pyttsx3"
