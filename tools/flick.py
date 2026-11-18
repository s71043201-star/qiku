"""Lamp flicker made from ONE picture: the lit tube is found by its brightness, and the frames only change how
bright the tube and its glow on the ceiling are. Lines, stains and shadows are never redrawn.
usage: python flick.py <base image> <out folder> <key>"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

src, out, key = sys.argv[1], sys.argv[2], sys.argv[3]
ROOM = len(sys.argv) > 4 and sys.argv[4] == 'room'   # 'room' = the lamp lights the whole picture
im = Image.open(src).convert('RGB')
W, H = im.size
a = np.asarray(im, dtype=np.float32)
lum = np.asarray(im.convert('L'), dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# the lit tube: the very bright pixels in the right half, upper part
tube = ((lum > 205) & (xx > 0.58 * W) & (yy < 0.64 * H)).astype(np.float32)
blur = lambda m, r: np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255
hot = ((lum > 238) & (xx > 0.58 * W) & (yy < 0.64 * H)).astype(np.float32)
core = np.clip(blur(hot, 2.5) * 1.5, 0, 1)         # the tube itself (only the white-hot part)
L0 = float(np.percentile(lum[(xx < 0.5 * W) & (yy > 0.3 * H) & (yy < 0.6 * H)], 60))  # the plain ceiling's brightness
TUBE_OFF = np.array([92, 88, 80], dtype=np.float32)  # an unlit tube: dull grey glass
near = blur(tube, 0.035 * W); near = near / near.max()   # the glow close to it
wide = blur(tube, 0.30 * W); wide = wide / wide.max()    # the light it throws across the ceiling
print('tube pixels: %.2f%%' % (tube.mean() * 100))


def frame(level):
    """level 1 = as drawn, 0 = tube off, >1 = flare"""
    d = 1 - level
    # the glow on the ceiling: take away the brightness ABOVE the ceiling's own level, so a lit patch fades to the
    # plain ceiling instead of turning into a dark stain; plus a gentle overall dimming on that side of the room
    reach = np.clip(wide * 2.2, 0, 1)   # wide and soft, so no edge shows where the glow used to be
    new = lum - d * 0.9 * np.maximum(lum - L0, 0) * reach
    k = (new / np.maximum(lum, 1)) * (1 - d * 0.20 * wide)
    if ROOM:   # this lamp is the only light in the room: when it goes, the whole room goes with it
        k = np.full_like(lum, 0.07 + 0.93 * min(level, 1.0) + 0.22 * max(level - 1, 0))
    o = a * np.clip(k, 0.05, 1.6)[..., None]
    c = core[..., None]
    glass = TUBE_OFF * (0.9 + 0.1 * (lum[..., None] / 255))
    o = o * (1 - c) + (glass + (a - glass) * max(level, 0)) * c   # the tube: from white down to dull grey glass
    if level > 1:
        o = o + (level - 1) * 150 * near[..., None] + (level - 1) * 40 * wide[..., None]
    return Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))


levels = [1, 0.75, 0.5, 0.25, 0.06, 1.12, 1.28]
frames = [frame(v) for v in levels]
for i, f in enumerate(frames):
    f.save(os.path.join(out, '%s_k%d.png' % (key, i + 1)))
sh = Image.new('RGB', (260 * 7, 260))
for i, f in enumerate(frames):
    sh.paste(f.resize((260, 260)), (i * 260, 0))
sh.save(os.path.join(out, key + '_levels.jpg'), quality=82)
seq = [0, 2, 0, 4, 3, 0, 0, 5, 0, 1, 4, 6, 0, 0]
dur = [900, 70, 110, 90, 70, 500, 300, 70, 400, 60, 100, 80, 700, 300]
frames[0].resize((560, 560)).save(os.path.join(out, key + '_flicker.gif'), save_all=True,
                                  append_images=[frames[i].resize((560, 560)) for i in seq[1:]], duration=dur, loop=0)
