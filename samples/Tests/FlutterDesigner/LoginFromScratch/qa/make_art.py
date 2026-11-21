"""Original artwork for the QA login screen (drawn here with Pillow, no third-party art): hanging lamps."""
import sys
from PIL import Image, ImageDraw, ImageFilter


def lamp(path, h=300, w=120, cord=0.55):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = w // 2
    cy = int(h * cord)
    d.line([(cx, 0), (cx, cy)], fill=(255, 255, 255, 230), width=3)
    # glow
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([cx - 50, cy + 10, cx + 50, cy + 110], fill=(255, 245, 200, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    im = Image.alpha_composite(im, glow)
    d = ImageDraw.Draw(im)
    # shade (trapezoid) + bulb
    d.polygon([(cx - 14, cy), (cx + 14, cy), (cx + 40, cy + 46), (cx - 40, cy + 46)], fill=(255, 255, 255, 245))
    d.ellipse([cx - 14, cy + 36, cx + 14, cy + 64], fill=(255, 236, 160, 255))
    im.save(path)


if __name__ == "__main__":
    out = sys.argv[1]
    lamp(out + "/lamp_long.png", 300, 120, 0.55)
    lamp(out + "/lamp_short.png", 220, 120, 0.4)
    print("ok")
