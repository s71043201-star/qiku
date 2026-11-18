"""Flowers nodding in a breeze, made from ONE picture. Each flower is bent about the foot of its own stem (the foot
stays put, the head moves most), each with its own rhythm, so the row never moves in step. Nothing else changes.
The flowers are located from the hand-made frames (where the picture differed), then those frames are not used.
usage: python petals.py <folder with flowers_f1..f4.png> <out folder> [frames] [max px]"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

src, out = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 36
AMP = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
im = Image.open(os.path.join(src, 'flowers_f1.png')).convert('RGB')
W, H = im.size
a = np.asarray(im, dtype=np.float32)
g = [np.asarray(Image.open(os.path.join(src, 'flowers_f%d.png' % i)).convert('L'), dtype=np.float32) for i in (1, 2, 3, 4)]
diff = np.maximum.reduce([np.abs(x - g[0]) for x in g[1:]]) > 12
diff[int(0.70 * H):] = False

# find the flowers: rows first (gaps in the row profile), then the seven in each row (gaps in the column profile)
def runs(v, gap):
    idx = np.where(v)[0]; out_ = []; s = idx[0]; p = idx[0]
    for i in idx[1:]:
        if i - p > gap:
            out_.append((s, p)); s = i
        p = i
    out_.append((s, p)); return out_

boxes = []
for (r0, r1) in runs(diff.sum(axis=1) > 2, 6):
    if r1 - r0 < 15:
        continue
    for (c0, c1) in runs(diff[r0:r1 + 1].sum(axis=0) > 0, 5):
        if c1 - c0 >= 8:
            boxes.append((c0, r0, c1, r1))
print('flowers found:', len(boxes))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rng = np.random.RandomState(7)
par = []
for (c0, r0, c1, r1) in boxes:
    m = np.zeros((H, W), dtype=np.float32)
    m[max(0, r0 - 5):r1 + 3, max(0, c0 - 6):c1 + 7] = 1
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255
    base = r1 + 2.0; h = max(base - (r0 - 5), 1)
    lever = np.clip((base - yy) / h, 0, 1) ** 1.4        # 0 at the foot of the stem, 1 at the top of the flower
    k1, k2 = rng.choice([1, 2]), rng.choice([3, 4, 5])   # whole cycles per loop: a slow nod and a quicker tremble
    par.append((m * lever, k1, k2, rng.rand() * 6.28, rng.rand() * 6.28, 0.6 + 0.4 * rng.rand(), (c0 + c1) / 2 / W))


def sample(dx):
    x = np.clip(xx + dx, 0, W - 1.001)
    x0 = x.astype(np.int32); wx = (x - x0)[..., None]
    y0 = yy.astype(np.int32)
    return a[y0, x0] * (1 - wx) + a[y0, x0 + 1] * wx


frames = []
for i in range(N):
    t = 2 * np.pi * i / N
    dx = np.zeros((H, W), dtype=np.float32)
    for (w, k1, k2, p1, p2, amt, cx) in par:
        gust = 0.35 + 0.65 * (0.5 - 0.5 * np.cos(t - 2 * np.pi * cx * 0.8)) ** 1.5   # a breath of wind crossing the bed
        bend = amt * gust * (0.75 * np.sin(k1 * t + p1) + 0.25 * np.sin(k2 * t + p2) + 0.35)   # mostly leaning down-wind
        dx -= AMP * bend * w
    fr = Image.fromarray(np.clip(sample(dx), 0, 255).astype(np.uint8))
    frames.append(fr); fr.save(os.path.join(out, 'flowers_p%d.png' % (i + 1)))
moved = np.maximum.reduce([np.abs(np.asarray(f, dtype=np.float32) - a).max(axis=2) for f in frames]) > 2
ys, xs = np.where(moved)
print('changed box: %.3f %.3f %.3f %.3f' % (xs.min() / W, ys.min() / H, xs.max() / W, ys.max() / H))
frames[0].save(os.path.join(out, 'flowers_sway.gif'), save_all=True, append_images=frames[1:], duration=110, loop=0)
x0, y0, x1, y1 = int(0.09 * W), int(0.34 * H), int(0.89 * W), int(0.70 * H)
c = [f.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS) for f in frames]
c[0].save(os.path.join(out, 'flowers_sway_big.gif'), save_all=True, append_images=c[1:], duration=110, loop=0)
