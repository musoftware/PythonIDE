"""Generates the artwork of the Flutter designer templates (original, drawn programmatically with Pillow).

    python -m radide.flutterdesign.templates.art        # rewrites radide/flutterdesign/templates/assets/*.png

Every image is abstract geometry (gradients, waves, blobs, simple product silhouettes) made by this script, so
the templates carry no third-party artwork. Licence: same as RAD IDE (the images are part of it).
Output is deterministic (fixed random seed). Pillow is needed only to regenerate the files.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "assets"
SS = 2          # supersampling factor (anti-aliasing)


def _rgba(h: str, a: int = 255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _lerp(c1, c2, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def _gradient(size, c1, c2, angle_deg=90):
    from PIL import Image
    w, h = size
    img = Image.new("RGBA", size)
    px = img.load()
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    span = abs(w * dx) + abs(h * dy)
    for y in range(h):
        for x in range(w):
            t = ((x - w / 2) * dx + (y - h / 2) * dy) / span + 0.5
            px[x, y] = _lerp(c1, c2, min(1, max(0, t)))
    return img


def _canvas(w, h, bg=(0, 0, 0, 0)):
    from PIL import Image
    return Image.new("RGBA", (w * SS, h * SS), bg)


def _finish(img, name):
    from PIL import Image
    w, h = img.size
    img = img.resize((w // SS, h // SS), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / name, optimize=True)
    return OUT / name


def _wave_poly(w, h, base, amp, freq, phase, steps=120):
    pts = [(0, h)]
    for i in range(steps + 1):
        x = w * i / steps
        y = base + amp * math.sin(freq * 2 * math.pi * i / steps + phase)
        pts.append((x, y))
    pts.append((w, h))
    return pts


def _blob(cx, cy, r, wobble, seed, n=9, steps=180):
    rnd = random.Random(seed)
    amps = [rnd.uniform(-wobble, wobble) for _ in range(n)]
    phases = [rnd.uniform(0, 2 * math.pi) for _ in range(n)]
    pts = []
    for i in range(steps):
        a = 2 * math.pi * i / steps
        rr = r * (1 + sum(amps[k] * math.sin((k + 2) * a + phases[k]) for k in range(3)) / 3)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _shadow(img, box, radius, blur=18, alpha=70):
    from PIL import Image, ImageDraw, ImageFilter
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse(box, fill=(20, 20, 40, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur * SS))
    return Image.alpha_composite(img, sh)


# ----------------------------------------------------------------------------------------------- art
def login_waves():
    """Header art for the Login template: layered waves over an indigo-violet gradient, with soft orbs."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = 1080, 760
    img = _gradient((w * SS // 4, h * SS // 4), _rgba("#4F5BD5"), _rgba("#9D6BF2"), 60).resize((w * SS, h * SS))
    orbs = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(orbs)
    for cx, cy, r, a in ((160, 140, 120, 60), (900, 120, 180, 45), (760, 420, 70, 70), (300, 470, 40, 80)):
        d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=(255, 255, 255, a))
    orbs = orbs.filter(ImageFilter.GaussianBlur(3 * SS))
    img = Image.alpha_composite(img, orbs)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for base, amp, freq, ph, col in ((560, 40, 1.2, 0.3, (255, 255, 255, 50)),
                                     (610, 34, 1.6, 1.9, (255, 255, 255, 90)),
                                     (680, 26, 1.1, 3.6, (255, 255, 255, 255))):
        d.polygon([(x * SS, y * SS) for x, y in _wave_poly(w, h, base, amp, freq, ph)], fill=col)
    img = Image.alpha_composite(img, layer)
    return _finish(img, "login_waves.png")


def signup_blobs():
    """Translucent overlapping blobs for the Sign-up background (transparent PNG)."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = 900, 900
    img = _canvas(w, h)
    for cx, cy, r, col, seed in ((300, 320, 260, "#FFFFFF", 3), (620, 520, 220, "#FFD6E8", 7),
                                 (420, 640, 140, "#C9F0FF", 11)):
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).polygon([(x * SS, y * SS) for x, y in _blob(cx, cy, r, 0.35, seed)],
                                    fill=_rgba(col, 70))
        img = Image.alpha_composite(img, lay.filter(ImageFilter.GaussianBlur(2 * SS)))
    return _finish(img, "signup_blobs.png")


def onboarding(n: int):
    """Three onboarding illustrations: stacked cards, a chart on a disc, and an orbit (transparent PNGs)."""
    from PIL import Image, ImageDraw
    w = h = 800
    img = _canvas(w, h)
    palettes = [("#FFB86B", "#FF6B8A", "#6B7BFF"), ("#4FD1C5", "#3B82F6", "#FBBF24"),
                ("#A78BFA", "#F472B6", "#34D399")]
    c1, c2, c3 = palettes[n - 1]
    bg = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(bg).polygon([(x * SS, y * SS) for x, y in _blob(400, 400, 300, 0.25, 20 + n)],
                               fill=_rgba(c1, 60))
    img = Image.alpha_composite(img, bg)
    d = ImageDraw.Draw(img)
    S = SS
    if n == 1:      # stacked cards with lines (a feed)
        for i, (dx, dy, col) in enumerate(((-60, 70, c3), (-20, 20, c2), (30, -30, "#FFFFFF"))):
            x0, y0 = 220 + dx, 250 + dy
            img = _shadow(img, [(x0 + 20) * S, (y0 + 260) * S, (x0 + 360) * S, (y0 + 300) * S], 0, 14, 50)
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([x0 * S, y0 * S, (x0 + 380) * S, (y0 + 270) * S], 34 * S, fill=_rgba(col))
            if col == "#FFFFFF":
                d.ellipse([(x0 + 30) * S, (y0 + 30) * S, (x0 + 100) * S, (y0 + 100) * S], fill=_rgba(c2))
                for k, ln in enumerate((220, 160, 250, 190)):
                    y = y0 + 130 + k * 30
                    d.rounded_rectangle([(x0 + 30) * S, y * S, (x0 + 30 + ln) * S, (y + 14) * S], 7 * S,
                                        fill=_rgba("#E6E8F5"))
                d.rounded_rectangle([(x0 + 120) * S, (y0 + 45) * S, (x0 + 300) * S, (y0 + 62) * S], 8 * S,
                                    fill=_rgba(c3, 200))
    elif n == 2:    # chart on a disc
        img = _shadow(img, [190 * S, 600 * S, 610 * S, 660 * S], 0, 16, 60)
        d = ImageDraw.Draw(img)
        d.ellipse([170 * S, 170 * S, 630 * S, 630 * S], fill=_rgba("#FFFFFF"))
        bars = [0.35, 0.55, 0.45, 0.8, 0.65]
        for i, v in enumerate(bars):
            x0 = 265 + i * 58
            top = 520 - 250 * v
            d.rounded_rectangle([x0 * S, top * S, (x0 + 36) * S, 520 * S], 12 * S,
                                fill=_rgba(c2 if i != 3 else c3))
        pts = [(283 + i * 58, 520 - 250 * v - 40) for i, v in enumerate(bars)]
        d.line([(x * S, y * S) for x, y in pts], fill=_rgba(c1, 255), width=8 * S, joint="curve")
        for x, y in pts:
            d.ellipse([(x - 10) * S, (y - 10) * S, (x + 10) * S, (y + 10) * S], fill=_rgba("#FFFFFF"),
                      outline=_rgba(c1), width=5 * S)
    else:           # orbit with planets
        for r, wd in ((270, 4), (190, 4)):
            d.ellipse([(400 - r) * S, (400 - r) * S, (400 + r) * S, (400 + r) * S], outline=_rgba(c2, 120),
                      width=wd * S)
        img = _shadow(img, [300 * S, 470 * S, 500 * S, 520 * S], 0, 14, 60)
        d = ImageDraw.Draw(img)
        d.ellipse([300 * S, 300 * S, 500 * S, 500 * S], fill=_rgba(c1))
        d.ellipse([335 * S, 330 * S, 395 * S, 360 * S], fill=_rgba("#FFFFFF", 120))
        for ang, r, pr, col in ((-40, 270, 34, c2), (130, 270, 22, c3), (200, 190, 26, "#FFFFFF"),
                                (40, 190, 16, c2)):
            a = math.radians(ang)
            cx, cy = 400 + r * math.cos(a), 400 + r * math.sin(a)
            d.ellipse([(cx - pr) * S, (cy - pr) * S, (cx + pr) * S, (cy + pr) * S], fill=_rgba(col))
    return _finish(img, f"onboarding_{n}.png")


def avatar(n: int):
    """Geometric avatars: a coloured disc with a simple head-and-shoulders silhouette."""
    from PIL import ImageDraw
    w = h = 256
    bgs = [("#FFB4A2", "#E5989B"), ("#A0C4FF", "#7B9CFF"), ("#B9FBC0", "#64D3A0"), ("#FFD6A5", "#FFAD5A")]
    skin = ["#8D5524", "#F1C27D", "#C68642", "#FFDBAC"][n - 1]
    hair = ["#2B2118", "#6B4226", "#1B1B1B", "#B5651D"][n - 1]
    shirt = ["#3D5A80", "#EE6C4D", "#293241", "#5E60CE"][n - 1]
    img = _gradient((w * SS, h * SS), _rgba(bgs[n - 1][0]), _rgba(bgs[n - 1][1]), 45)
    d = ImageDraw.Draw(img)
    S = SS
    d.ellipse([48 * S, 170 * S, 208 * S, 330 * S], fill=_rgba(shirt))              # shoulders
    d.rounded_rectangle([110 * S, 140 * S, 146 * S, 185 * S], 12 * S, fill=_rgba(skin))   # neck
    d.ellipse([78 * S, 58 * S, 178 * S, 168 * S], fill=_rgba(skin))                # face
    if n % 2:
        d.pieslice([72 * S, 46 * S, 184 * S, 150 * S], 180, 360, fill=_rgba(hair))  # short hair
    else:
        d.ellipse([66 * S, 44 * S, 190 * S, 140 * S], fill=_rgba(hair))
        d.rectangle([66 * S, 92 * S, 92 * S, 200 * S], fill=_rgba(hair))
        d.rectangle([164 * S, 92 * S, 190 * S, 200 * S], fill=_rgba(hair))
        d.ellipse([84 * S, 80 * S, 172 * S, 168 * S], fill=_rgba(skin))
    return _finish(img, f"avatar_{n}.png")


def product(kind: str):
    """Simple product silhouettes on transparent background: headphones, watch, speaker, plant."""
    from PIL import ImageDraw
    w = h = 600
    img = _canvas(w, h)
    S = SS
    img = _shadow(img, [150 * S, 500 * S, 450 * S, 545 * S], 0, 16, 70)
    d = ImageDraw.Draw(img)
    if kind == "headphones":
        d.arc([140 * S, 110 * S, 460 * S, 430 * S], 180, 360, fill=_rgba("#2D3142"), width=34 * S)
        for x in (120, 380):
            d.rounded_rectangle([x * S, 250 * S, (x + 100) * S, 440 * S], 44 * S, fill=_rgba("#2D3142"))
            d.rounded_rectangle([(x + 18) * S, 270 * S, (x + 82) * S, 420 * S], 30 * S, fill=_rgba("#EF8354"))
    elif kind == "watch":
        d.rounded_rectangle([235 * S, 60 * S, 365 * S, 540 * S], 40 * S, fill=_rgba("#4F5D75"))
        d.ellipse([170 * S, 170 * S, 430 * S, 430 * S], fill=_rgba("#2D3142"))
        d.ellipse([195 * S, 195 * S, 405 * S, 405 * S], fill=_rgba("#F4F1EA"))
        d.line([300 * S, 300 * S, 300 * S, 225 * S], fill=_rgba("#2D3142"), width=10 * S)
        d.line([300 * S, 300 * S, 355 * S, 330 * S], fill=_rgba("#EF8354"), width=8 * S)
        d.ellipse([290 * S, 290 * S, 310 * S, 310 * S], fill=_rgba("#2D3142"))
        d.rounded_rectangle([425 * S, 280 * S, 450 * S, 320 * S], 6 * S, fill=_rgba("#2D3142"))
    elif kind == "speaker":
        d.rounded_rectangle([180 * S, 70 * S, 420 * S, 520 * S], 60 * S, fill=_rgba("#3A6EA5"))
        d.ellipse([230 * S, 120 * S, 370 * S, 260 * S], fill=_rgba("#1E3A5F"))
        d.ellipse([268 * S, 158 * S, 332 * S, 222 * S], fill=_rgba("#A9C7E8"))
        d.ellipse([210 * S, 290 * S, 390 * S, 470 * S], fill=_rgba("#1E3A5F"))
        d.ellipse([260 * S, 340 * S, 340 * S, 420 * S], fill=_rgba("#A9C7E8"))
    else:           # plant
        for ang, ln, col in ((-60, 190, "#2A9D8F"), (-100, 230, "#40916C"), (-130, 180, "#52B788"),
                             (-30, 150, "#74C69D"), (-80, 260, "#2D6A4F")):
            a = math.radians(ang)
            cx, cy = 300 + ln * 0.55 * math.cos(a), 330 + ln * 0.55 * math.sin(a)
            d.ellipse([(cx - 46) * S, (cy - 92) * S, (cx + 46) * S, (cy + 92) * S], fill=_rgba(col))
        d.polygon([(200 * S, 320 * S), (400 * S, 320 * S), (370 * S, 520 * S), (230 * S, 520 * S)],
                  fill=_rgba("#E76F51"))
        d.rounded_rectangle([185 * S, 300 * S, 415 * S, 345 * S], 12 * S, fill=_rgba("#F4A261"))
    return _finish(img, f"product_{kind}.png")


def profile_cover():
    """A soft mesh-like gradient cover for the Profile template."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = 1080, 600
    img = _gradient((w * SS // 4, h * SS // 4), _rgba("#FF9A8B"), _rgba("#6A82FB"), 20).resize((w * SS, h * SS))
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for cx, cy, r, col in ((200, 120, 260, "#FECFEF"), (850, 450, 300, "#4FACFE"), (600, 80, 180, "#F9D423")):
        d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=_rgba(col, 110))
    img = Image.alpha_composite(img, lay.filter(ImageFilter.GaussianBlur(60 * SS)))
    return _finish(img, "profile_cover.png")


def main() -> None:
    files = [login_waves(), signup_blobs(), profile_cover()]
    files += [onboarding(i) for i in (1, 2, 3)]
    files += [avatar(i) for i in (1, 2, 3, 4)]
    files += [product(k) for k in ("headphones", "watch", "speaker", "plant")]
    for f in files:
        print(f.name, f.stat().st_size)


if __name__ == "__main__":
    main()
