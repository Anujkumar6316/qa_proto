"""Annotate a raw page screenshot with the snapshot's component boxes + refs.

Pure image work (Pillow). Coordinates come straight from the driver snapshot,
so every annotation is bound to what was actually measured — no guessing.
"""

from __future__ import annotations

import io
from typing import Any

_VIEWPORT = (1280, 900)
_COLORS = ["#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#00C7BE",
           "#0A84FF", "#5E5CE6", "#BF5AF2"]


def annotate_image(raw_png: bytes, components: list[dict[str, Any]],
                   out_path: Any) -> bool:
    """Draw each component's box + ref label onto *raw_png* and save to out_path.

    Returns True on success; False if Pillow is missing or the bytes are not a
    readable image (the crawl itself must never fail because of annotation).
    """
    try:
        from PIL import Image, ImageDraw  # lazy import; pillow is optional at runtime

        img = Image.open(io.BytesIO(raw_png)).convert("RGB")
        draw = ImageDraw.Draw(img)
        vw, vh = _VIEWPORT
        sx = img.width / vw
        sy = img.height / vh

        for i, comp in enumerate(components):
            box = comp.get("box")
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                continue
            try:
                x1, y1, x2, y2 = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
            except (TypeError, ValueError):
                continue
            if x2 <= x1 or y2 <= y1:
                continue  # degenerate box — nothing meaningful to draw
            ax1, ay1 = max(0, round(x1 * sx)), max(0, round(y1 * sy))
            ax2, ay2 = min(img.width - 1, round(x2 * sx)), min(img.height - 1, round(y2 * sy))
            color = _COLORS[i % len(_COLORS)]
            draw.rectangle([ax1, ay1, ax2, ay2], outline=color, width=2)

            ref = str(comp.get("ref") or f"@e{i + 1}")
            tw = max(10, 7 * len(ref) + 4)
            th = 14
            lx = ax1
            ly = ay1 - th - 1 if ay1 - th - 1 >= 0 else ay1 + 1
            draw.rectangle([lx, ly, lx + tw, ly + th], fill=color)
            draw.text((lx + 3, ly + 1), ref, fill="#000000")

        img.save(str(out_path), format="PNG")
        return True
    except Exception:
        return False
