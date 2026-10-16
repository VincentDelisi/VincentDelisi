"""
Turn a photo into ascii.txt for the profile card.
Usage:  python ascii_art.py photo.jpg [columns]
Tip: a tightly cropped headshot on a plain background works best.
"""
import sys
from PIL import Image, ImageOps

RAMP = " .:-=+*#%@"   # dim -> bright (bright pixels get dense characters on the dark card)


def convert(path, cols=40):
    img = ImageOps.autocontrast(Image.open(path).convert("L"))
    w, h = img.size
    rows = max(1, int(h / w * cols * 0.48))   # characters are ~2x taller than wide
    img = img.resize((cols, rows))
    px = list(img.getdata())
    lines = []
    for r in range(rows):
        row = px[r * cols:(r + 1) * cols]
        lines.append("".join(RAMP[p * (len(RAMP) - 1) // 255] for p in row).rstrip())
    return "\n".join(lines)


if __name__ == "__main__":
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    art = convert(sys.argv[1], cols)
    open("ascii.txt", "w", encoding="utf-8").write(art + "\n")
    print(art)
