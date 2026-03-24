from __future__ import annotations

from pathlib import Path

from darwix_app.models import VoiceProfile
from darwix_app.services.emotion_service import GeminiEmotionService
from darwix_app.services.tts_service import TextToSpeechService


class EmpathyEngine:
    def __init__(self, api_key: str, model_name: str, output_dir: Path):
        self.emotion_service = GeminiEmotionService(api_key=api_key, model_name=model_name)
        self.tts_service = TextToSpeechService(output_dir=output_dir)

    def build_voice_profile(self, emotion: str, intensity: float, voice_id: str | None, gender: str | None) -> VoiceProfile:
        strength = max(0.0, min(intensity, 1.0))
        voice = self.tts_service.resolve_voice(voice_id=voice_id, preferred_gender=gender)

        emotion_profiles = {
            "happy": ("+12%", "+8%", "+8Hz", "Bright, upbeat delivery with a warm lift."),
            "excited": ("+22%", "+14%", "+18Hz", "Faster and higher-energy delivery for strong enthusiasm."),
            "neutral": ("+0%", "+0%", "+0Hz", "Balanced, even delivery for neutral content."),
            "concerned": ("-10%", "-4%", "-8Hz", "Gentler and slightly lower delivery to sound careful and empathetic."),
            "sad": ("-16%", "-8%", "-16Hz", "Softer, slower delivery for low-energy emotional content."),
            "frustrated": ("-6%", "+4%", "-10Hz", "Measured delivery that acknowledges tension without sounding flat."),
            "angry": ("+8%", "+12%", "-18Hz", "Sharper, stronger delivery with heavier projection for angry tone."),
            "inquisitive": ("-2%", "+2%", "+10Hz", "Light upward pitch to sound curious and engaged."),
            "surprised": ("+14%", "+8%", "+22Hz", "Quick, lifted delivery to reflect surprise."),
        }
        base_rate, base_volume, base_pitch, description = emotion_profiles.get(
            emotion,
            emotion_profiles["neutral"],
        )

        return VoiceProfile(
            emotion=emotion,
            voice_name=voice["voice"],
            rate=self._scale_percent(base_rate, strength),
            volume=self._scale_percent(base_volume, strength),
            pitch=self._scale_hz(base_pitch, strength),
            description=description,
        )

    @staticmethod
    def _scale_percent(value: str, strength: float) -> str:
        sign = "+" if value.startswith("+") else "-"
        amount = float(value[1:-1])
        scaled = round(amount * max(strength, 0.35), 1)
        return f"{sign}{scaled}%"

    @staticmethod
    def _scale_hz(value: str, strength: float) -> str:
        sign = "+" if value.startswith("+") else "-"
        amount = float(value[1:-2])
        scaled = round(amount * max(strength, 0.35), 1)
        return f"{sign}{scaled}Hz"

    def synthesize(self, text: str, filename_root: str, voice_id: str | None, gender: str | None) -> dict:
        emotion_result = self.emotion_service.classify(text)
        voice_profile = self.build_voice_profile(
            emotion=emotion_result.emotion,
            intensity=emotion_result.intensity,
            voice_id=voice_id,
            gender=gender,
        )
        audio_path, tts_provider = self.tts_service.synthesize(
            text=text,
            profile=voice_profile,
            filename_root=filename_root,
        )
        return {
            "text": text,
            "emotion": emotion_result.emotion,
            "intensity": round(emotion_result.intensity, 3),
            "parameters": {
                "voice": voice_profile.voice_name,
                "rate": voice_profile.rate,
                "volume": voice_profile.volume,
                "pitch": voice_profile.pitch,
            },
            "mapping_reason": voice_profile.description,
            "analysis_reason": emotion_result.rationale,
            "analysis_provider": emotion_result.provider,
            "tts_provider": tts_provider,
            "filename": audio_path.name,
        }
