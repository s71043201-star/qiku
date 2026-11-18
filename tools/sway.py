"""Wind in the leaves, made from ONE picture. Only pixels inside the canopy mask move; the trunk, the mountains,
the house and everything else stay perfectly still.
The motion is a gust that travels across the canopy from left to right: leaves are pushed the same way (to the
right and a little down), quickly, then swing back slowly, and they tremble while the gust is on them.
usage: python sway.py <base image> <out folder> <key> [frames] [push px]"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

src, out, key = sys.argv[1], sys.argv[2], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 20
AMP = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0
im = Image.open(src).convert('RGB')
W, H = im.size
a = np.asarray(im, dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# What may move: only the fringe of leaves that shows against the sky on the left. The inside of the crown is one
# solid dark mass (nothing to see there), and the branches, trunk, mountains and house must stay still.
fx = xx / W; fy = yy / H
g0 = np.asarray(im.convert('L').filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)
img8 = lambda m: Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
arr = lambda i: np.asarray(i, dtype=np.float32) / 255
sky = (g0 > 92) & (fy < 0.31) & (fx < 0.62)
near_sky = arr(img8(sky).filter(ImageFilter.MaxFilter(27)))          # within about 13 px of open sky
dark = arr(img8(g0 < 80).filter(ImageFilter.MaxFilter(5)))           # the leaf shapes, with a little air round them
fringe = arr(img8(near_sky * dark).filter(ImageFilter.GaussianBlur(2.5)))
# the mountains must not move: stay above the ridge (traced from the picture, as fractions of the height)
ridge = np.interp(fx, [0, 0.13, 0.29, 0.43, 0.57, 1], [0.25, 0.224, 0.27, 0.29, 0.27, 0.27])
above_ridge = np.clip((ridge - 0.012 - fy) / 0.03, 0, 1)
# the big limb that runs from the trunk out to the left must not move: a band along it is kept out
x1, y1, x2, y2 = 0.36, 0.135, 0.70, 0.235
tpar = np.clip(((fx - x1) * (x2 - x1) + (fy - y1) * (y2 - y1)) / ((x2 - x1) ** 2 + (y2 - y1) ** 2), 0, 1)
dist = np.hypot(fx - (x1 + tpar * (x2 - x1)), fy - (y1 + tpar * (y2 - y1)))
off_limb = np.clip((dist - 0.022) / 0.02, 0, 1)
right_end = np.clip((0.56 - fx) / 0.06, 0, 1)                         # further right there is only trunk and branches
mask = fringe * above_ridge * off_limb * right_end
vis = a.copy(); vis[..., 1] = np.maximum(vis[..., 1], mask * 255)
Image.fromarray(vis.astype(np.uint8)).crop((0, 0, W, int(0.36 * H))).save(os.path.join(out, key + '_moving.jpg'), quality=85)


def field(seed, scale):
    r = np.random.RandomState(seed)
    n = Image.fromarray((r.rand(H, W) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(scale))
    f = np.asarray(n, dtype=np.float32)
    f = (f - f.mean()) / (f.std() + 1e-6)
    return np.clip(f, -2.2, 2.2) / 2.2


clump = field(11, 60)            # each clump of leaves answers the wind a little earlier or later ...
give = 0.65 + 0.35 * field(12, 40)  # ... and bends a little more or less
tw = [field(s, 7) for s in (21, 22, 23, 24)]  # the fine trembling of single leaves


def sample(dx, dy):
    x = np.clip(xx + dx, 0, W - 1.001); y = np.clip(yy + dy, 0, H - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32)
    wx = (x - x0)[..., None]; wy = (y - y0)[..., None]
    return (a[y0, x0] * (1 - wx) * (1 - wy) + a[y0, x0 + 1] * wx * (1 - wy) + a[y0 + 1, x0] * (1 - wx) * wy + a[y0 + 1, x0 + 1] * wx * wy)


frames = []
for i in range(N):
    t = 2 * np.pi * i / N
    ph = t - 2 * np.pi * (fx * 0.9) + 1.1 * clump       # the gust arrives later the further right a leaf is
    ph = ph + 0.55 * np.sin(ph)                         # pushed over quickly, swinging back slowly
    g = (0.5 - 0.5 * np.cos(ph)) ** 1.6                 # 0 = at rest (most of the time), 1 = fully bent
    c3, s3 = np.cos(3 * t), np.sin(3 * t)
    push = AMP * mask * give * g
    # sampling at x - push moves what is drawn to the right (down-wind); leaves also dip a little
    dx = -push + 0.9 * mask * g * (tw[0] * c3 + tw[1] * s3)
    dy = -0.28 * push + 0.7 * mask * g * (tw[2] * c3 + tw[3] * s3)
    fr = Image.fromarray(np.clip(sample(dx, dy), 0, 255).astype(np.uint8))
    frames.append(fr)
    fr.save(os.path.join(out, '%s_s%d.png' % (key, i + 1)))
frames[0].resize((560, 560)).save(os.path.join(out, key + '_sway.gif'), save_all=True,
                                  append_images=[x.resize((560, 560)) for x in frames[1:]], duration=120, loop=0)
d = [np.abs(np.asarray(x, dtype=np.float32) - a).mean(axis=2) for x in frames]
print('frames', N, 'max changed outside mask:', max(float((x * (mask == 0)).max()) for x in d),
      'change per frame inside canopy:', ' '.join('%.0f' % x[mask > 0.3].mean() for x in d))
rows = np.where(mask.max(axis=1) > 0)[0]
print('moving rows: 0 ..', int(rows.max()), 'of', H, '= %.3f' % ((rows.max() + 2) / H))
