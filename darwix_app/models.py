from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionResult:
    emotion: str
    intensity: float
    rationale: str
    provider: str


@dataclass(frozen=True)
class VoiceProfile:
    emotion: str
    voice_name: str
    rate: str
    volume: str
    pitch: str
    description: str


@dataclass(frozen=True)
class StoryPanel:
    caption: str
    prompt: str
    image_filename: str
    source: str
