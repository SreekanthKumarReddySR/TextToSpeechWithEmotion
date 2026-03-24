from __future__ import annotations

import json
from typing import Any

from google import genai

from darwix_app.models import EmotionResult


EMOTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "emotion": {
            "type": "string",
            "enum": [
                "happy",
                "excited",
                "neutral",
                "concerned",
                "sad",
                "frustrated",
                "angry",
                "inquisitive",
                "surprised",
            ],
        },
        "intensity": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["emotion", "intensity", "rationale"],
}


class GeminiEmotionService:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    def classify(self, text: str) -> EmotionResult:
        if not self.api_key:
            return self._fallback_result(text, "Gemini API key missing. Used keyword fallback.")

        try:
            client = genai.Client(api_key=self.api_key)
            prompt = (
                "Classify the emotional tone of the text for expressive speech synthesis. "
                "Return JSON only with emotion, intensity, rationale. "
                "Emotion must be one of happy, excited, neutral, concerned, sad, frustrated, angry, inquisitive, surprised. "
                "Intensity must be a float from 0.0 to 1.0.\n\n"
                f"Text: {text}"
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": EMOTION_SCHEMA,
                    "temperature": 0.2,
                },
            )
            data = json.loads(response.text)
            return EmotionResult(
                emotion=data["emotion"],
                intensity=max(0.0, min(float(data["intensity"]), 1.0)),
                rationale=data["rationale"].strip(),
                provider="gemini",
            )
        except Exception:
            return self._fallback_result(
                text,
                "Gemini request failed during runtime. Used local fallback analysis.",
            )

    def _fallback_result(self, text: str, rationale: str) -> EmotionResult:
        lowered = text.lower()
        mapping = [
            ("angry", ["angry", "furious", "outraged"]),
            ("frustrated", ["frustrated", "issue", "delay", "problem"]),
            ("excited", ["excited", "thrilled", "amazing", "fantastic"]),
            ("happy", ["happy", "glad", "great", "wonderful"]),
            ("concerned", ["concerned", "worried", "careful"]),
            ("sad", ["sad", "sorry", "upset", "unfortunately"]),
            ("inquisitive", ["why", "how", "what", "could you"]),
            ("surprised", ["surprised", "wow", "unexpected"]),
        ]

        for emotion, tokens in mapping:
            if any(token in lowered for token in tokens):
                return EmotionResult(
                    emotion=emotion,
                    intensity=0.72,
                    rationale=rationale,
                    provider="fallback",
                )

        return EmotionResult(
            emotion="neutral",
            intensity=0.28,
            rationale=rationale,
            provider="fallback",
        )
