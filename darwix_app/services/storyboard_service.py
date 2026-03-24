from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

from darwix_app.models import StoryPanel


PANEL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "panels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "prompt": {"type": "string"},
                },
                "required": ["caption", "prompt"],
            },
        }
    },
    "required": ["panels"],
}


class StoryboardService:
    def __init__(self, api_key: str, model_name: str, image_model: str, output_dir: Path):
        self.api_key = api_key
        self.model_name = model_name
        self.image_model = image_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_storyboard(self, narrative: str, style: str) -> dict:
        segments = self.segment_narrative(narrative)
        prompts = self.enhance_prompts(segments=segments, style=style)
        panels = [self.generate_panel(caption=item["caption"], prompt=item["prompt"]) for item in prompts]
        return {"style": style, "segments": segments, "panels": [panel.__dict__ for panel in panels]}

    def segment_narrative(self, narrative: str) -> list[str]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", narrative.strip()) if part.strip()]
        if len(sentences) >= 3:
            return sentences[:4]

        clauses = [part.strip() for part in re.split(r",|;|\n", narrative.strip()) if part.strip()]
        merged = clauses if len(clauses) >= 3 else [narrative.strip()]
        return merged[:4]

    def enhance_prompts(self, segments: list[str], style: str) -> list[dict[str, str]]:
        if not self.api_key:
            return [self._fallback_prompt(segment, style) for segment in segments]

        try:
            client = genai.Client(api_key=self.api_key)
            joined = "\n".join(f"{index + 1}. {segment}" for index, segment in enumerate(segments))
            prompt = (
                "You are creating a storyboard for a sales narrative. "
                "Return JSON only with a panels array. "
                "For each segment, preserve the meaning in caption and write a richer visual prompt. "
                "Keep all prompts stylistically consistent.\n\n"
                f"Style: {style}\n"
                f"Segments:\n{joined}"
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": PANEL_SCHEMA,
                    "temperature": 0.6,
                },
            )
            data = json.loads(response.text)
            panels = data.get("panels", [])
            if not panels:
                raise ValueError("No panels returned")
            return panels[: len(segments)]
        except Exception:
            return [self._fallback_prompt(segment, style) for segment in segments]

    def generate_panel(self, caption: str, prompt: str) -> StoryPanel:
        filename = f"{uuid4().hex}.png"
        output_path = self.output_dir / filename

        try:
            if not self.api_key:
                raise ValueError("Image generation key unavailable")

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.image_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )

            image_saved = False
            for candidate in getattr(response, "candidates", []) or []:
                for part in getattr(candidate.content, "parts", []) or []:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        data = inline.data
                        if isinstance(data, str):
                            data = data.encode("utf-8")
                        image = Image.open(BytesIO(data))
                        image.save(output_path)
                        image_saved = True
                        break
                if image_saved:
                    break

            if not image_saved:
                raise ValueError("Gemini image bytes not found")

            return StoryPanel(caption=caption, prompt=prompt, image_filename=filename, source="gemini")
        except Exception:
            self._create_placeholder_image(output_path=output_path, caption=caption, prompt=prompt)
            return StoryPanel(caption=caption, prompt=prompt, image_filename=filename, source="fallback")

    @staticmethod
    def _fallback_prompt(segment: str, style: str) -> dict[str, str]:
        return {
            "caption": segment,
            "prompt": f"{style} storyboard panel, clean composition, cinematic lighting, visualizing: {segment}",
        }

    @staticmethod
    def _create_placeholder_image(output_path: Path, caption: str, prompt: str):
        image = Image.new("RGB", (1024, 768), "#efe2d3")
        draw = ImageDraw.Draw(image)
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        draw.rounded_rectangle((40, 40, 984, 728), radius=24, fill="#fffaf4", outline="#d8c4ad", width=3)
        draw.text((80, 90), caption[:90], fill="#6d2f1f", font=title_font)
        draw.text((80, 160), prompt[:340], fill="#3f332c", font=body_font, spacing=6)
        image.save(output_path)
