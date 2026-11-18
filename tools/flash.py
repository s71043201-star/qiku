"""Lightning seen through a window, made from ONE picture: the panes inside a box go white, the glow spills round
the window, and whatever is already bright in the room (the shine on the floor, the edges of the walls) is lifted.
Two frames: a2 = the flash, a3 = the afterglow. Nothing is redrawn.
usage: python flash.py <base image> <out folder> <key> x0 y0 x1 y1"""
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
thr = float(np.percentile(lum[box], 55))
pane = ((lum > thr) & box).astype(np.float32)
blur = lambda m, r: np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255
core = np.clip(blur(pane, 1.0) * 1.3, 0, 1)
near = blur(box.astype(np.float32), 0.03 * W); near = near / near.max()
room = blur(box.astype(np.float32), 0.22 * W); room = room / room.max()
cold = np.array([238, 240, 236], dtype=np.float32)   # lightning is a colder white than the lamps


def frame(k):
    c = (core * 0.9 * k)[..., None]
    o = a * (1 - c) + cold * c
    o = o + (70 * k * near)[..., None]
    o = o + a * (0.9 * k * (0.25 + 0.75 * room))[..., None]      # lift what is already lit; black stays black
    return Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))


fr = [im, frame(1.0), frame(0.4)]
for i, f in enumerate(fr):
    f.save(os.path.join(out, '%s_z%d.png' % (key, i + 1)))
sh = Image.new('RGB', (W * 3 // 2, H // 2))
for i, f in enumerate(fr):
    sh.paste(f.resize((W // 2, H // 2)), (i * (W // 2), 0))
sh.save(os.path.join(out, key + '_flash.jpg'), quality=85)
seq = [0, 0, 1, 0, 1, 2, 0, 0, 0]
dur = [1500, 800, 70, 60, 110, 180, 900, 900, 900]
fr[0].save(os.path.join(out, key + '_flash.gif'), save_all=True, append_images=[fr[i] for i in seq[1:]], duration=dur, loop=0)
print('pane threshold %.0f, pane pixels %.2f%%' % (thr, pane.mean() * 100))
