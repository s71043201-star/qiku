"""A lit window that wavers, made from ONE picture: the bright panes inside a box are found by brightness and the
frames only change how bright they (and the little glow around them) are. Nothing is redrawn.
usage: python glow.py <base image> <out folder> <key> x0 y0 x1 y1   (the box round the window, as fractions)"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

src, out, key = sys.argv[1], sys.argv[2], sys.argv[3]
x0, y0, x1, y1 = [float(v) for v in sys.argv[4:8]]
im = Image.open(src).convert('RGB')
W, H = im.size
a = np.asarray(im, dtype=np.float32)
lum = np.asarray(im.convert('L'), dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
box = (xx > x0 * W) & (xx < x1 * W) & (yy > y0 * H) & (yy < y1 * H)
thr = max(120.0, float(np.percentile(lum[box], 80)))
pane = ((lum > thr) & box).astype(np.float32)
blur = lambda m, r: np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255
core = np.clip(blur(pane, 1.2) * 1.4, 0, 1)
near = blur(pane, 0.022 * W); near = near / max(near.max(), 1e-6)
print('window pixels: %.2f%% threshold %.0f' % (pane.mean() * 100, thr))


def frame(level):
    d = 1 - level
    o = a * (1 - d * 0.45 * near)[..., None]
    c = core[..., None]
    o = o * (1 - c) + a * (0.22 + 0.78 * level) * c
    if level > 1:
        o = o + (level - 1) * 120 * near[..., None]
    return Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))


levels = [1, 0.8, 0.6, 0.38, 1.15]
frames = [frame(v) for v in levels]
for i, f in enumerate(frames):
    f.save(os.path.join(out, '%s_w%d.png' % (key, i + 1)))
d = np.abs(np.asarray(frames[3], dtype=np.float32) - a).max(axis=2)
ys, xs = np.where(d > 2)
print('changed box: %.3f %.3f %.3f %.3f' % (xs.min() / W, ys.min() / H, xs.max() / W, ys.max() / H))
cx0, cy0, cx1, cy1 = int(0.38 * W), int(0.30 * H), int(0.76 * W), int(0.60 * H)
sh = Image.new('RGB', ((cx1 - cx0) * 5 // 2, (cy1 - cy0) // 2))
for i, f in enumerate(frames):
    t = f.crop((cx0, cy0, cx1, cy1)); t = t.resize((t.width // 2, t.height // 2)); sh.paste(t, (i * t.width, 0))
sh.save(os.path.join(out, key + '_window.jpg'), quality=85)
