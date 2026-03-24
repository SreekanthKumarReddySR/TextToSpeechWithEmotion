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
        return {
            "style": style,
            "segments": segments,
            "panels": [panel.__dict__ for panel in panels],
        }

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
                "You are creating a visual storyboard from a narrative. "
                "Return JSON only with a panels array. "
                "For each segment, keep the caption concise and produce a highly visual, cinematic image prompt. "
                "Prefer photorealistic detail, shallow depth of field, realistic textures, human presence where appropriate, and continuity across panels. "
                "Never mention text overlays, labels, captions, posters, collage, split screens, or graphic design layouts in the prompt.\n\n"
                f"Style: {style}\n"
                f"Segments:\n{joined}"
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": PANEL_SCHEMA,
                    "temperature": 0.55,
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
            if self.image_model.startswith("imagen-"):
                response = client.models.generate_images(
                    model=self.image_model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="16:9",
                        person_generation="allow_adult",
                    ),
                )
                generated = getattr(response, "generated_images", None) or []
                if not generated:
                    raise ValueError("Imagen returned no images")
                image_bytes = generated[0].image.image_bytes
                Image.open(BytesIO(image_bytes)).save(output_path)
                source = "imagen"
            else:
                response = client.models.generate_content(
                    model=self.image_model,
                    contents=[prompt],
                )
                image_saved = False
                for part in getattr(response, "parts", []) or []:
                    if getattr(part, "inline_data", None) is not None:
                        image = part.as_image()
                        image.save(output_path)
                        image_saved = True
                        break
                if not image_saved:
                    raise ValueError("Gemini image bytes not found")
                source = "gemini image"

            return StoryPanel(caption=caption, prompt=prompt, image_filename=filename, source=source)
        except Exception:
            self._create_placeholder_image(output_path=output_path, caption=caption, prompt=prompt)
            return StoryPanel(caption=caption, prompt=prompt, image_filename=filename, source="illustrated fallback")

    @staticmethod
    def _fallback_prompt(segment: str, style: str) -> dict[str, str]:
        return {
            "caption": segment,
            "prompt": (
                f"{style}, photorealistic cinematic still, detailed environment, human presence where relevant, "
                f"storyboard panel visualizing: {segment}"
            ),
        }

    @staticmethod
    def _create_placeholder_image(output_path: Path, caption: str, prompt: str):
        width, height = 1280, 720
        palette = {
            "bg_top": "#2d211e",
            "bg_bottom": "#b88e63",
            "frame": "#f5eadb",
            "frame_line": "#a1754f",
            "gold": "#ba8d33",
            "gold_dark": "#7b5a18",
            "fabric": "#5b463d",
            "fabric_shadow": "#3a2c27",
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
        glow_draw.ellipse((120, 60, 1160, 660), fill=(255, 221, 168, 60))
        glow = glow.filter(ImageFilter.GaussianBlur(42))
        image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle((56, 44, 1224, 676), radius=34, fill=palette["frame"], outline=palette["frame_line"], width=4)
        draw.rounded_rectangle((90, 84, 1190, 640), radius=26, fill="#fbf4eb", outline=palette["frame_line"], width=3)

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
        draw.rounded_rectangle((118, 106, 640, 150), radius=16, fill="#fff8f0", outline=palette["frame_line"], width=2)
        draw.text((136, 120), caption[:92], fill=palette["ink"], font=title_font)
        image.save(output_path)

    @staticmethod
    def _draw_key_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.ellipse((150, 155, 470, 500), fill=palette["skin"])
        draw.polygon([(155, 455), (305, 585), (410, 392), (286, 258)], fill=palette["skin"])
        draw.rounded_rectangle((650, 130, 1030, 560), radius=42, fill=palette["fabric"], outline=palette["fabric_shadow"], width=5)
        draw.polygon([(650, 195), (820, 104), (1030, 104), (1030, 258)], fill="#6a554b")
        draw.rounded_rectangle((760, 300, 998, 520), radius=24, outline="#8f7566", width=4)
        draw.line((760, 368, 998, 368), fill="#8f7566", width=4)
        draw.ellipse((452, 262, 602, 412), fill=palette["gold"], outline=palette["gold_dark"], width=6)
        draw.ellipse((494, 304, 560, 370), fill="#f6edde", outline=palette["gold_dark"], width=4)
        draw.rounded_rectangle((588, 325, 860, 350), radius=10, fill=palette["gold"], outline=palette["gold_dark"], width=4)
        draw.rectangle((812, 309, 842, 364), fill=palette["gold"], outline=palette["gold_dark"])
        draw.rectangle((841, 325, 868, 364), fill=palette["gold"], outline=palette["gold_dark"])
        draw.rectangle((867, 309, 894, 364), fill=palette["gold"], outline=palette["gold_dark"])

    @staticmethod
    def _draw_door_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.rectangle((135, 158, 1125, 594), fill="#d8c0a4")
        draw.rounded_rectangle((420, 126, 770, 618), radius=16, fill="#6a4738", outline="#3b241b", width=6)
        draw.rounded_rectangle((456, 182, 734, 576), radius=10, outline="#8d6754", width=4)
        draw.ellipse((686, 370, 718, 402), fill=palette["gold"], outline=palette["gold_dark"], width=3)
        draw.ellipse((230, 220, 570, 540), fill=(255, 230, 176))

    @staticmethod
    def _draw_letter_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.rounded_rectangle((220, 174, 1060, 580), radius=30, fill="#7b604f", outline="#4e382d", width=5)
        draw.rounded_rectangle((278, 206, 1006, 540), radius=22, fill=palette["paper"], outline="#b89773", width=3)
        for offset in range(0, 230, 32):
            draw.line((340, 276 + offset, 946, 276 + offset), fill="#bda07f", width=3)
        draw.polygon([(278, 206), (642, 392), (1006, 206)], fill="#f6ead7", outline="#b89773")

    @staticmethod
    def _draw_memory_scene(draw: ImageDraw.ImageDraw, palette: dict[str, str]):
        draw.ellipse((245, 155, 1025, 610), fill="#d9bea1", outline="#b18d67", width=4)
        draw.rounded_rectangle((360, 225, 910, 565), radius=28, fill="#f9f2e9", outline="#b18d67", width=4)
        draw.line((418, 318, 850, 318), fill="#c5a27d", width=4)
        draw.line((418, 388, 850, 388), fill="#c5a27d", width=4)
        draw.line((418, 456, 770, 456), fill="#c5a27d", width=4)

    @staticmethod
    def _mix_hex(start: str, end: str, amount: float) -> str:
        start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
        end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
        mixed = tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * amount) for i in range(3))
        return "#{:02x}{:02x}{:02x}".format(*mixed)
