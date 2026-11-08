"""Photo-style render of the board: black solder mask, gold (ENIG) pads, white silkscreen.
Usage: render_pretty.py board.kicad_pcb outdir"""
import os, subprocess, sys, io
import numpy as np
import cairosvg
from PIL import Image, ImageFilter, ImageDraw

pcb, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
W = 1400
tmp = os.path.join(out, "_layers"); os.makedirs(tmp, exist_ok=True)

def layer(name, mirror=False):
    f = os.path.join(tmp, name.replace(".", "_") + ("_m" if mirror else "") + ".svg")
    cmd = ["kicad-cli", "pcb", "export", "svg", "--page-size-mode", "2", "--exclude-drawing-sheet",
           "--black-and-white", "-l", name + ",Edge.Cuts", "-o", f, pcb]
    if mirror: cmd.insert(4, "-m")
    subprocess.run(cmd, check=True, capture_output=True)
    png = cairosvg.svg2png(url=f, output_width=W, background_color="white")
    a = np.array(Image.open(io.BytesIO(png)).convert("L"))
    return a < 128

def side(prefix, mirror):
    edge = layer("Edge.Cuts", mirror)
    cu, mask, silk = layer(prefix + ".Cu", mirror), layer(prefix + ".Mask", mirror), layer(prefix + ".SilkS", mirror)
    h, w = edge.shape
    # board area = flood fill from the centre inside the outline
    img = Image.fromarray(np.where(edge, 0, 255).astype(np.uint8)).copy()
    ImageDraw.floodfill(img, (w // 2, h // 2), 128)
    board = (np.array(img) == 128) | edge
    rgb = np.zeros((h, w, 3), np.float32) + 255
    rgb[board] = (18, 18, 20)                                   # black mask
    cu_only = cu & ~edge
    rgb[board & cu_only] = (38, 38, 42)                         # copper under the mask
    gold = board & mask & ~edge
    rgb[gold] = (214, 170, 82)                                   # ENIG pads
    rgb[board & silk & ~mask] = (245, 245, 245)                  # silkscreen
    # light shading for depth
    im = Image.fromarray(rgb.clip(0, 255).astype(np.uint8))
    shade = Image.new("L", (w, h), 0); d = ImageDraw.Draw(shade)
    d.ellipse([w * 0.05, h * 0.0, w * 0.75, h * 0.6], fill=28)
    shade = shade.filter(ImageFilter.GaussianBlur(120))
    im = Image.composite(Image.new("RGB", (w, h), (255, 255, 255)), im,
                         Image.fromarray((np.array(shade) * board).astype(np.uint8)))
    # transparent background
    alpha = Image.fromarray((board * 255).astype(np.uint8))
    im.putalpha(alpha)
    return im

for name, pre, mir in (("pcb_top.png", "F", False), ("pcb_bottom.png", "B", True)):
    side(pre, mir).save(os.path.join(out, name))
    print("wrote", name)
