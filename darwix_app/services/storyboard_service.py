from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
                "You are creating a storyboard for a narrative. "
                "Return JSON only with a panels array. "
                "For each segment, preserve the meaning in caption and write a richer visual prompt. "
                "Keep all prompts stylistically consistent and cinematic.\n\n"
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
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
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
            return StoryPanel(caption=caption, prompt=prompt, image_filename=filename, source="illustrated fallback")

    @staticmethod
    def _fallback_prompt(segment: str, style: str) -> dict[str, str]:
        return {
            "caption": segment,
            "prompt": f"{style} storyboard panel, cinematic composition, visualizing: {segment}",
        }

    @staticmethod
    def _create_placeholder_image(output_path: Path, caption: str, prompt: str):
        width, height = 1024, 768
        palette = {
            "bg_top": "#3c2e2b",
            "bg_bottom": "#d8b187",
            "card": "#f8efe3",
            "line": "#a47a54",
            "gold": "#ba8d33",
            "gold_dark": "#7b5a18",
            "fabric": "#59453d",
            "fabric_shadow": "#3b2d28",
            "skin": "#d8b49a",
            "paper": "#efe0c8",
            "ink": "#2f241f",
        }

        image = Image.new("RGB", (width, height), palette["bg_bottom"])
        draw = ImageDraw.Draw(image)

        for y in range(height):
            blend = y / height
            color = StoryboardService._mix_hex(palette["bg_top"], palette["bg_bottom"], blend)
            draw.line((0, y, width, y), fill=color)

        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((120, 60, 880, 680), fill=(255, 214, 150, 70))
        glow = glow.filter(ImageFilter.GaussianBlur(36))
        image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle((54, 48, 970, 714), radius=34, fill=palette["card"], outline=palette["line"], width=4)

        text = f"{caption} {prompt}".lower()
        if "key" in text:
            StoryboardService._draw_key_scene(draw, palette)
        elif "door" in text or "gate" in text:
            StoryboardService._draw_door_scene(draw, palette)
        elif "letter" in text or "note" in text or "paper" in text:
            StoryboardService._draw_letter_scene(draw, palette)
        else:
            StoryboardService._draw_memory_scene(draw, palette)

        title_font = ImageFont.load_default()
        label = caption[:88]
        draw.rounded_rectangle((86, 78, 538, 126), radius=18, fill="#fff7ee", outline=palette["line"], width=2)
        draw.text((104, 94), label, fill=palette["ink"], font=title_font)
        image.save(output_path)

    @staticmethod
    def _draw_key_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.ellipse((130, 150, 410, 460), fill=palette["skin"], outline=None)
        draw.polygon([(120, 420), (270, 520), (360, 365), (260, 245)], fill=palette["skin"])
        draw.rounded_rectangle((515, 160, 860, 575), radius=38, fill=palette["fabric"], outline=palette["fabric_shadow"], width=4)
        draw.polygon([(515, 215), (660, 132), (860, 132), (860, 250)], fill="#6e574d")
        draw.rounded_rectangle((612, 300, 828, 500), radius=22, outline="#8e7466", width=4)
        draw.line((612, 360, 828, 360), fill="#8e7466", width=4)
        draw.ellipse((360, 250, 480, 370), fill=palette["gold"], outline=palette["gold_dark"], width=5)
        draw.ellipse((395, 285, 445, 335), fill=palette["card"], outline=palette["gold_dark"], width=3)
        draw.rounded_rectangle((455, 300, 670, 322), radius=10, fill=palette["gold"], outline=palette["gold_dark"], width=4)
        draw.rectangle((630, 288, 655, 335), fill=palette["gold"], outline=palette["gold_dark"])
        draw.rectangle((654, 300, 678, 335), fill=palette["gold"], outline=palette["gold_dark"])
        draw.rectangle((677, 288, 700, 335), fill=palette["gold"], outline=palette["gold_dark"])

    @staticmethod
    def _draw_door_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.rectangle((140, 160, 884, 612), fill="#dbc4a7")
        draw.rounded_rectangle((360, 138, 668, 620), radius=14, fill="#6a4738", outline="#3b241b", width=6)
        draw.rounded_rectangle((392, 184, 636, 574), radius=10, outline="#8d6754", width=4)
        draw.ellipse((598, 362, 626, 390), fill=palette["gold"], outline=palette["gold_dark"], width=3)
        draw.ellipse((220, 210, 488, 510), fill=(255, 227, 165))

    @staticmethod
    def _draw_letter_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.rounded_rectangle((180, 176, 842, 590), radius=30, fill="#7b604f", outline="#4e382d", width=5)
        draw.rounded_rectangle((230, 206, 790, 548), radius=22, fill=palette["paper"], outline="#b89773", width=3)
        for offset in range(0, 230, 32):
            draw.line((280, 272 + offset, 742, 272 + offset), fill="#bda07f", width=3)
        draw.polygon([(230, 206), (510, 382), (790, 206)], fill="#f6ead7", outline="#b89773")

    @staticmethod
    def _draw_memory_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.ellipse((210, 154, 824, 640), fill="#d9bea1", outline="#b18d67", width=4)
        draw.rounded_rectangle((292, 210, 744, 566), radius=26, fill="#f9f2e9", outline="#b18d67", width=4)
        draw.line((340, 300, 696, 300), fill="#c5a27d", width=4)
        draw.line((340, 360, 696, 360), fill="#c5a27d", width=4)
        draw.line((340, 420, 630, 420), fill="#c5a27d", width=4)

    @staticmethod
    def _mix_hex(start: str, end: str, amount: float) -> str:
        start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
        end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
        mixed = tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * amount) for i in range(3))
        return "#{:02x}{:02x}{:02x}".format(*mixed)
