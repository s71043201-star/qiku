"""Align a redrawn 'eyes closed' frame to its base picture and keep only the eye area,
so the two frames are pixel-identical everywhere else.
usage: blink_align.py <base.jpg> <closed.png> <out.jpg> <check.jpg> [cx cy rx ry]  (fractions; optional manual eye ellipse)"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

base_p, closed_p, out_p, check_p = sys.argv[1:5]
manual = [float(v) for v in sys.argv[5:9]] if len(sys.argv) >= 9 else None
base = Image.open(base_p).convert('RGB')
N = base.size[0]
closed = Image.open(closed_p).convert('RGB')
S = 200
b = np.asarray(base.convert('L').resize((S, S)), dtype=np.float32)


def place(img_l, sc, dy, dx):
    w = int(round(S * sc))
    c = np.asarray(img_l.resize((w, w)), dtype=np.float32)
    canvas = np.zeros((S, S), dtype=np.float32)
    y0, x0 = (S - w) // 2 + dy, (S - w) // 2 + dx
    ys, xs, ye, xe = max(0, y0), max(0, x0), min(S, y0 + w), min(S, x0 + w)
    canvas[ys:ye, xs:xe] = c[ys - y0:ye - y0, xs - x0:xe - x0]
    return canvas


cl = closed.convert('L')
best = None
for sc in np.arange(0.90, 1.121, 0.01):
    for dy in range(-16, 17, 2):
        for dx in range(-16, 17, 2):
            err = float(np.abs(place(cl, sc, dy, dx) - b).mean())
            if best is None or err < best[0]:
                best = (err, sc, dy, dx)
err, sc, dy, dx = best
for ddy in (-1, 0, 1):
    for ddx in (-1, 0, 1):
        e = float(np.abs(place(cl, sc, dy + ddy, dx + ddx) - b).mean())
        if e < best[0]:
            best = (e, sc, dy + ddy, dx + ddx)
err, sc, dy, dx = best
W = int(round(N * sc))
k = N / S
layer = Image.new('RGB', (N, N))
layer.paste(closed.resize((W, W), Image.LANCZOS), (int(round((N - W) / 2 + dx * k)), int(round((N - W) / 2 + dy * k))))

if manual:
    cx, cy, rx, ry = manual
    m = Image.new('L', (N, N), 0)
    ImageDraw.Draw(m).ellipse([int(N * (cx - rx)), int(N * (cy - ry)), int(N * (cx + rx)), int(N * (cy + ry))], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(N * 0.008))
else:
    # find where the two frames differ most: that is the eyes
    d = np.abs(np.asarray(layer.convert('L'), dtype=np.float32) - np.asarray(base.convert('L'), dtype=np.float32))
    dm = Image.fromarray(np.clip(d, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(N * 0.018))
    da = np.asarray(dm, dtype=np.float32)
    da[int(N * 0.72):, :] = 0
    thr = max(da.max() * 0.5, 14)
    m = Image.fromarray(((da > thr) * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(int(N * 0.03) | 1)).filter(ImageFilter.GaussianBlur(N * 0.008))
out = base.copy()
out.paste(layer, (0, 0), m)
out.save(out_p, quality=84)
side = Image.new('RGB', (N * 3, N))
side.paste(base, (0, 0))
side.paste(out, (N, 0))
side.paste(Image.merge('RGB', (m, m, m)), (N * 2, 0))
side.resize((900, 300)).save(check_p)
cover = float((np.asarray(m) > 128).mean())
print('align', round(err, 2), round(float(sc), 2), dy, dx, 'mask', round(cover * 100, 1), '%')
