"""Narrator clips that are not dialogue lines (gen_voice.py only handles say()/it() lines).
Currently: the opening rhyme of the first night (人敲三 / 鬼敲四) and the title card of the second (念到名字的人 / 要答「有」).
usage: python tools/gen_narration.py <七窟_原型 folder>
needs: edge-tts, numpy, miniaudio, lameenc (same as gen_voice.py)"""
import asyncio, os, sys, tempfile
import numpy as np
import edge_tts, miniaudio, lameenc

root = sys.argv[1]
SR = 24000
# file name -> text. A low, slow voice; 鬼敲四 is slower and lower still.
CLIPS = {'n_knock3': ('人敲三', -34, -22), 'n_knock4': ('鬼敲四', -42, -34),
         # the second night's title card
         'n_roll1': ('念到名字的人', -34, -22), 'n_roll2': ('要答，有', -42, -34),
         # the third night's
         'n_sea1': ('她每天都在看海', -34, -22), 'n_sea2': ('窗外，沒有海', -42, -34),
         # the fourth night's
         'n_seven1': ('這是你，第七次來了', -34, -22), 'n_seven2': ('前六次，你都沒有撐到十五號', -42, -34),
         # the fifth night's
         'n_ku1': ('十五號', -34, -22), 'n_ku2': ('這一次，你要說什麼', -42, -34)}
VOICES = ['zh-TW-YunJheNeural', 'zh-CN-YunjianNeural']  # Taiwan voice first, fallback if it fails


async def synth(text, rate, pitch):
    for voice in VOICES:
        path = os.path.join(tempfile.gettempdir(), 'qiku_narr_%s_%d.mp3' % (voice, abs(hash(text)) % 10 ** 8))
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, voice, rate=f'{rate:+d}%', pitch=f'{pitch:+d}Hz').save(path)
                if os.path.getsize(path) > 800:
                    return voice, path
            except Exception:
                await asyncio.sleep(1.5)
    raise RuntimeError('no voice could say: ' + text)


def decode(path):
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=SR)
    a = np.frombuffer(d.samples, dtype=np.int16).astype(np.float32) / 32768.0
    idx = np.where(np.abs(a) > 0.012)[0]
    return a[max(0, idx[0] - 480): idx[-1] + 480] if len(idx) else a[:0]


def echo(a, taps, tail_ms):
    out = np.concatenate([a, np.zeros(int(SR * tail_ms / 1000), dtype=np.float32)])
    base = out.copy()
    for ms, g in taps:
        n = int(SR * ms / 1000)
        out[n:] += base[:-n] * g
    return out


def encode(a, path):
    peak = float(np.max(np.abs(a))) if len(a) else 0
    if peak > 0:
        a = a * (0.92 / peak)
    enc = lameenc.Encoder()
    enc.set_bit_rate(64); enc.set_in_sample_rate(SR); enc.set_channels(1); enc.set_quality(2)
    open(path, 'wb').write(enc.encode((a * 32767).astype(np.int16).tobytes()) + enc.flush())


async def main():
    for name, (text, rate, pitch) in CLIPS.items():
        if os.path.exists(os.path.join(root, 'voice', name + '.mp3')):
            continue
        voice, path = await synth(text, rate, pitch)
        a = echo(decode(path), [(140, 0.42), (300, 0.26), (520, 0.14), (800, 0.07)], 900)  # an empty hall
        out = os.path.join(root, 'voice', name + '.mp3')
        encode(a, out)
        print(name, text, voice, '%.1fs' % (len(a) / SR), os.path.getsize(out), 'bytes')

asyncio.run(main())
