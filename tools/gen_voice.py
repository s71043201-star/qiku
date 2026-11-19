"""Directed voice build: split each line into phrases, vary pace and pitch per phrase,
insert pauses, add per-role effects, and write one mp3 per line.
usage: python tools/gen_voice.py <七窟_原型 folder> [--all] [--only <text> ...]
By default only lines that have no clip yet are made (they get the next free v### numbers), so the
existing clips keep their files. --all rebuilds every clip from scratch and renumbers them.
--only makes just the missing lines that contain one of the given pieces of text."""
import re, json, os, sys, asyncio, hashlib, tempfile
import numpy as np
import edge_tts, miniaudio, lameenc

root = sys.argv[1]
SR = 24000
cache_dir = os.path.join(tempfile.gettempdir(), 'qiku_tts_cache')  # not next to this file: the decoder cannot open non-ASCII paths
os.makedirs(cache_dir, exist_ok=True)
p = os.path.join(root, 'index.html')
s = open(p, encoding='utf-8').read()
lines = re.findall(r"say\('([^']+)', '([^']+)'\)", s) + re.findall(r"voice\('([^']+)', '([^']+)'\)", s) \
    + [('牆裡的聲音', t) for t in re.findall(r"await it\('([^']+)'\)", s)]
seen = []
for l in lines:
    if l not in seen:
        seen.append(l)

F, Y, TWM = 'zh-TW-HsiaoChenNeural', 'zh-TW-HsiaoYuNeural', 'zh-TW-YunJheNeural'
J, X, YY, K = 'zh-CN-YunjianNeural', 'zh-CN-YunxiNeural', 'zh-CN-YunyangNeural', 'zh-CN-YunxiaNeural'
# role: voice, base rate %, base pitch Hz, pause multiplier
CN = {'老周': (J, -6, -12, 1.1), '吳會計': (YY, -10, -14, 1.0), '木伯': (J, -26, -26, 1.7), '高老師': (X, -10, -6, 1.15),
      '老王': (J, -18, -20, 1.35), '院長': (J, 4, -18, 1.25), '牆裡的聲音': (K, -26, -36, 1.9), '年輕的你': (X, 0, 2, 1.0)}
TW = {'老周': (TWM, -8, -22, 1.1), '吳會計': (TWM, -6, -10, 1.0), '木伯': (TWM, -26, -34, 1.7), '高老師': (TWM, -8, 0, 1.15),
      '老王': (TWM, -16, -16, 1.35), '院長': (TWM, 6, -10, 1.25), '牆裡的聲音': (K, -26, -36, 1.9), '年輕的你': (TWM, 2, 6, 1.0)}
cfg = {'護理長': (F, -6, -4, 1.0), '何太太': (Y, -8, -6, 1.1), '蘭嬸': (F, 4, -18, 0.9), '秀琴阿嬤': (Y, -12, -14, 1.0),
       '小孩的聲音': (Y, 6, 40, 0.9),
       '陳阿嬤': (F, -18, -24, 1.35)}

# per-line direction: substring -> list of (rate delta, pitch delta, volume) per phrase (last entry repeats)
DIRECT = {
    '是我去說的': [(0, 0, 1.0), (4, 4, 1.0), (14, 12, 1.05), (24, 22, 1.1)],
    '我沒有。我不記得': [(16, 16, 1.05), (22, 22, 1.1)],
    '樓下有人敲門': [(-16, -6, 0.6), (-22, -8, 0.55)],
    '報告！新兵報到': [(10, 12, 1.15), (14, 14, 1.2)],
    '你是。我記得你的臉': [(-18, -6, 0.9), (-10, -4, 0.9), (-16, -8, 0.85)],
    '嘴巴張開': [(-10, -6, 0.95), (-14, -8, 0.9)],
    '請等我一下': [(-4, 0, 1.0), (-8, -4, 1.0), (10, 8, 1.0), (16, 12, 0.95)],
    '我不會忘。我什麼都不會忘': [(-4, 0, 1.0), (-16, -10, 0.9)],
    '帶糖來': [(-18, -6, 0.85)],
    '這是你第七次來了': [(-12, -8, 0.95)],
    '聽到敲四下': [(-6, 0, 0.7), (-10, -4, 0.6), (-16, -6, 0.5)],
    '是人！': [(8, 20, 1.15)],
    '奇怪，他叫什麼名字': [(-10, -4, 0.85), (-18, -8, 0.75)],
    '我剛剛唱了什麼': [(-12, 6, 0.85)],
    '回去睡覺': [(-14, -8, 0.8)],
    '你每次都回來': [(-6, 0, 0.9), (-10, -4, 0.85), (-18, -10, 0.8)],
    '我昨天才來的。': [(-6, 0, 1.0), (-4, 0, 1.0), (-2, 0, 1.0)],
    # the woman at the window: slow and vague by default; the few lucid lines are quick, low and close
    '鍋爐室後面那道門': [(12, -8, 0.8)],
    '鑰匙在洗衣籃底下': [(12, -8, 0.8)],
    '不要相信院長': [(4, -12, 0.85)],
    '小聲一點': [(6, -10, 0.7)],
    '想起來的人': [(4, -8, 0.75), (2, -10, 0.75), (-8, -14, 0.7)],
    '下去的時候，帶給他': [(6, -8, 0.8), (2, -10, 0.8)],
    '不要說是誰給的': [(0, -12, 0.75)],
    '她幫你，是因為她要你下來': [(-6, -4, 0.95), (-16, -10, 0.85)],
    '不能叫媽媽': [(-4, 0, 1.0), (-8, -4, 0.95), (-18, -10, 0.85)],
}
PAUSE = {'，': 170, '、': 130, '。': 430, '？': 360, '！': 300, '…': 650, '—': 480, '；': 260, '：': 240}


def phrases(text):
    t = text.replace('「', '').replace('」', '').replace('——', '—').replace('……', '…')
    lead = 0
    while t and t[0] in PAUSE:
        lead += PAUSE[t[0]]
        t = t[1:]
    parts = re.findall(r'[^，。？！、；：…—]+[，。？！、；：…—]*', t)
    out = []
    for part in parts:
        m = re.match(r'([^，。？！、；：…—]+)([，。？！、；：…—]*)', part)
        out.append((m.group(1), m.group(2)))
    return lead, out


async def synth(voice, text, rate, pitch, sem):
    key = hashlib.md5(f'{voice}|{text}|{rate}|{pitch}'.encode('utf-8')).hexdigest()
    out = os.path.join(cache_dir, key + '.mp3')
    if os.path.exists(out) and os.path.getsize(out) > 800:
        return out
    async with sem:
        err = None
        for attempt in range(5):
            try:
                await edge_tts.Communicate(text, voice, rate=f'{rate:+d}%', pitch=f'{pitch:+d}Hz').save(out)
                if os.path.getsize(out) > 800:
                    return out
                err = 'empty'
            except Exception as e:
                err = e
            await asyncio.sleep(1.5 + attempt * 1.5)
        raise RuntimeError(f'{voice} {text}: {err}')


def decode(path):
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=SR)
    a = np.frombuffer(d.samples, dtype=np.int16).astype(np.float32) / 32768.0
    idx = np.where(np.abs(a) > 0.012)[0]
    if len(idx) == 0:
        return a[:0]
    pad = int(SR * 0.02)
    a = a[max(0, idx[0] - pad): idx[-1] + pad]
    f = min(int(SR * 0.008), len(a) // 2)
    if f > 0:
        ramp = np.linspace(0, 1, f, dtype=np.float32)
        a[:f] *= ramp
        a[-f:] *= ramp[::-1]
    return a


def silence(ms):
    return np.zeros(int(SR * ms / 1000), dtype=np.float32)


def echo(a, taps, tail_ms):
    out = np.concatenate([a, silence(tail_ms)])
    base = out.copy()
    for ms, g in taps:
        n = int(SR * ms / 1000)
        out[n:] += base[:-n] * g
    return out


def lowpass(a, alpha):
    out = np.empty_like(a)
    acc = 0.0
    for i in range(len(a)):
        acc += alpha * (a[i] - acc)
        out[i] = acc
    return out


def effects(who, a):
    if who == '牆裡的聲音':  # behind a wall: muffled, with a short stony echo
        a = lowpass(a, 0.32) * 1.5
        a = echo(a, [(85, 0.38), (170, 0.2), (290, 0.1)], 450)
    elif who in ('小孩的聲音', '年輕的你'):  # a dream: distant and washed out
        a = echo(a, [(120, 0.35), (260, 0.2), (420, 0.1)], 600) * 0.9
    return a


def encode(a, path):
    peak = float(np.max(np.abs(a))) if len(a) else 0
    if peak > 0.97:
        a = a * (0.97 / peak)
    enc = lameenc.Encoder()
    enc.set_bit_rate(64)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode((a * 32767).astype(np.int16).tobytes()) + enc.flush()
    open(path, 'wb').write(data)


only = sys.argv[sys.argv.index('--only') + 1:] if '--only' in sys.argv else []


async def main():
    sem = asyncio.Semaphore(3)
    try:
        await synth(TWM, '歡迎，慢慢來。', -6, 0, sem)
        cfg.update(TW)
        print('male voices: Taiwan')
    except Exception:
        cfg.update(CN)
        print('male voices: fallback')
    old = {} if '--all' in sys.argv else json.loads(re.search(r"/\*VOICE\*/(.*?)/\*END\*/", s, re.S).group(1))
    nxt = max([int(v[1:]) for v in old.values()] + [-1]) + 1
    ids = {}
    plan = []
    for i, (who, text) in enumerate(seen):
        if who + '|' + text in old:
            continue
        if only and not any(k in text for k in only):
            continue
        ids[i] = 'v%03d' % nxt
        nxt += 1
        voice, br, bp, pm = cfg[who]
        lead, ph = phrases(text)
        direct = next((v for k, v in DIRECT.items() if k in text), None)
        segs = []
        n = len(ph)
        for j, (body, punct) in enumerate(ph):
            dr = dp = 0
            vol = 1.0
            if direct:
                dr, dp, vol = direct[min(j, len(direct) - 1)]
            else:
                if n > 1:
                    if j == 0:
                        dr += 3
                    elif j == n - 1:
                        dr -= 9
                        dp -= 5
                    else:
                        dr += 5 if j % 2 else -3
                if len(body) <= 2:
                    dr -= 14
                if '？' in punct:
                    dp += 10
                if '！' in punct:
                    dr += 6
                    dp += 9
                if '…' in punct:
                    dr -= 10
            say_text = body + (punct[0] if punct and punct[0] in '？！。' else '')
            pause = sum(PAUSE.get(c, 0) for c in punct) * pm if j < n - 1 else 0
            if len(body) <= 2 and j < n - 1:
                pause *= 1.3
            segs.append((voice, say_text, br + dr, bp + dp, vol, pause))
        plan.append((i, who, lead * pm, segs))
    tasks = {}
    for _, _, _, segs in plan:
        for voice, t, r, pt, _, _ in segs:
            tasks[(voice, t, r, pt)] = None
    keys = list(tasks)
    res = await asyncio.gather(*[synth(v, t, r, pt, sem) for v, t, r, pt in keys])
    paths = dict(zip(keys, res))
    vmap = dict(old)
    for i, who, lead, segs in plan:
        chunks = [silence(lead)] if lead else []
        for voice, t, r, pt, vol, pause in segs:
            chunks.append(decode(paths[(voice, t, r, pt)]) * vol)
            if pause:
                chunks.append(silence(pause))
        a = effects(who, np.concatenate(chunks))
        a = np.concatenate([silence(40), a, silence(120)])
        vid = ids[i]
        encode(a, os.path.join(root, 'voice', vid + '.mp3'))
        vmap[who + '|' + seen[i][1]] = vid
    html = open(p, encoding='utf-8').read()
    html2, k = re.subn(r"/\*VOICE\*/.*?/\*END\*/", lambda m: '/*VOICE*/' + json.dumps(vmap, ensure_ascii=False) + '/*END*/', html, count=1, flags=re.S)
    assert k == 1
    open(p, 'w', encoding='utf-8').write(html2)
    print('lines', len(seen), 'new', len(ids), 'phrases', len(keys), 'clips', len(vmap))

asyncio.run(main())
