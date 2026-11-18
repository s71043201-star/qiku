"""A daytime version of a night picture, made from the same drawing: every scratched line is kept, the picture is
only lit differently. Daylight comes in through the window in the box, floods the room from there, and the lamp on
the ceiling is no longer the main light.
usage: python daylight.py <night image> <out image> x0 y0 x1 y1 [strength]"""
import sys
import numpy as np
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = [float(v) for v in sys.argv[3:7]]
K = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
im = Image.open(src).convert('RGB')
W, H = im.size
a = np.asarray(im, dtype=np.float32) / 255
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
box = ((xx > x0 * W) & (xx < x1 * W) & (yy > y0 * H) & (yy < y1 * H)).astype(np.float32)
blur = lambda m, r: np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255
lum = a.mean(axis=2)
near = blur(box, 0.035 * W); near = near / near.max()
room = blur(box, 0.30 * W); room = room / room.max()
# 1. open up the shadows everywhere (the lines get lighter, pure black stays black)
#    done on the brightness only, with the gain capped and faded out in the near-black, so the speckle hidden in the
#    darkest areas of the file is not blown up into coloured noise
sm = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255
gain = np.minimum(sm ** (1 / (1 + 0.75 * K)) / np.maximum(sm, 0.02), 3.2)
gain = 1 + (gain - 1) * np.clip((sm - 0.035) / 0.05, 0, 1)
grey = lum[..., None]
o = (grey + (a - grey) * 0.8) * gain[..., None]     # a touch less colour: daylight is flatter than lamplight
# 2. more light the closer to the window, and overall a brighter exposure
o = o * (1.05 + 0.55 * K * room)[..., None]
# 3. the window itself: daylight, almost white, spilling a little round the frame
pane = blur(((lum > np.percentile(lum[box > 0], 45)) & (box > 0)).astype(np.float32), 1.0)
day = np.array([0.96, 0.94, 0.86], dtype=np.float32)
c = np.clip(pane * 1.2 * K, 0, 0.92)[..., None]
o = o * (1 - c) + day * c
o = o + (0.22 * K * near)[..., None] * day
# 4. a faint haze of daylight in the air, so the far end is not a black hole
o = o + (0.05 * K * room)[..., None] * day
Image.fromarray((np.clip(o, 0, 1) * 255).astype(np.uint8)).save(dst, quality=92)
sh = Image.new('RGB', (W * 2, H)); sh.paste(im, (0, 0)); sh.paste(Image.open(dst), (W, 0))
sh.resize((1200, 600)).save(dst.rsplit('.', 1)[0] + '_cmp.jpg', quality=85)
