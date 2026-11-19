"""哔哔啵啵合成引擎 —— 移植自 hakihakii/bibibobo（MIT）。

原文不到一百行 JS：
  https://github.com/hakihakii/bibibobo/blob/main/bibibobo.js

五步，一步不多：
  1. 一条抗混叠锯齿波（polyBLEP）
  2. 两个带通滤波器捏出口型 —— 每张嘴就是两个共振峰频率
  3. 一个字一声，同一个字用哈希定音高和口型，所以永远同一声
  4. 每个声线一组音阶
  5. 标点管语气：问号尾音上扬，感叹整句抬三个半音，省略号压低

这里不做音库，纯算。所以文件只有几 KB，也不依赖 numpy 以外任何东西。
"""
from __future__ import annotations

import math
import re
import wave
from pathlib import Path

import numpy as np

__all__ = ["VOICES", "VOWELS", "synth", "write_wav", "syllables", "hash_of"]

TAU = math.pi * 2.0

# 五种口型：每种只是两个共振峰频率（Hz），对应「啊」「衣」「呜」这类张嘴形状。
VOWELS = [
    (800.0, 1200.0),
    (400.0, 2200.0),
    (350.0, 800.0),
    (600.0, 1700.0),
    (300.0, 2600.0),
]

# 音高/语速刻度的基准：400Hz 不移调，13 字每秒是默认节奏
BASE_PITCH = 400.0
BASE_UPS = 13.0

# 声线参数：音阶（MIDI 音高）、共振峰倍率、单字时长上限、时长占位、
# 字头小滑音、句尾下落、增益、默认字间隔
VOICES: dict[str, dict] = {
    # 大肥鱼：E5 G5 A5 B5 C6，共振峰乘 1.25（更尖），字头有个很短的小滑音
    "fish": {
        "scale": [76, 79, 81, 83, 84],
        "formant": 1.25, "maxDur": 0.13, "hold": 0.8,
        "chirp": 1.5, "fall": 0.0, "gain": 0.16, "step": 0.13,
    },
    # 路墨：D4 E4 G4 A4，共振峰乘 0.9，句尾轻轻往下落
    "lumo": {
        "scale": [62, 64, 67, 69],
        "formant": 0.9, "maxDur": 0.2, "hold": 0.7,
        "chirp": 0.0, "fall": -2.0, "gain": 0.17, "step": 0.16,
    },
}

# 一个汉字算一声，一串英文或数字算一声（与原文正则一致）
_SYL = re.compile(r"[A-Za-z_/.0-9]+|[\u4e00-\u9fff]")

# 按标点切句，每句各套一条语气规则
_SENT = re.compile(r"[^？?！!。.，,、；;…\n]+[？?！!。.，,、；;…]*")


def hash_of(s: str) -> int:
    """同一个字永远得到同一个数，所以同一个字永远是同一声。"""
    h = 7
    for ch in s:
        h = (h * 31 + ord(ch)) % 9973
    return h


def syllables(s: str) -> list[str]:
    """切成一声一声：一个汉字一声，一串英文数字一声。"""
    return _SYL.findall(s)


def _bandpass_resp(freqs: np.ndarray, fc: float, sr: int, q: float) -> np.ndarray:
    """RBJ 二阶带通的频率响应。

    原文是逐样本的状态变量滤波器；这里换成频域相乘，等价且快得多
    （一个字一次 rfft，150 字也不到 30ms）。
    """
    fc = min(float(fc), sr / 6.0)
    w0 = TAU * fc / sr
    alpha = math.sin(w0) / (2.0 * q)
    b0, b1, b2 = alpha, 0.0, -alpha
    a0, a1, a2 = 1.0 + alpha, -2.0 * math.cos(w0), 1.0 - alpha
    z = np.exp(-1j * TAU * freqs / sr)
    return np.abs((b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z))


def _render_one(out: np.ndarray, sr: int, t: float, m: float, dur: float,
                v: dict, glide: float = 0.0, vowel: int = 0) -> None:
    """把一声写进 out：音高 m（MIDI 音高，可带小数），时长 dur 秒，glide 是结尾滑几个半音。"""
    if dur <= 0:
        return
    a, b = VOWELS[vowel % len(VOWELS)]
    start = int(t * sr)
    end = min(start + int(dur * sr), out.size)
    n = end - start
    if n <= 0:
        return

    x = np.arange(n, dtype=np.float64) / sr

    # 音高曲线：基准 + 结尾滑音 + 字头小滑音 + 一点颤音
    mf = m + glide * (x / dur) + v["chirp"] * np.exp(-x * 30.0)
    freq = 440.0 * np.power(2.0, (mf - 69.0) / 12.0) * (1.0 + 0.012 * np.sin(TAU * 6.0 * x))
    dt = freq / sr

    # 抗混叠锯齿波：polyBLEP 在跳变处补两段，相位周期累加
    ph = np.cumsum(dt)
    ph -= np.floor(ph)
    s = 2.0 * ph - 1.0
    low = ph < dt
    if low.any():
        tt = ph[low] / dt[low]
        s[low] -= tt + tt - tt * tt - 1.0
    high = ph > 1.0 - dt
    if high.any():
        tt = (ph[high] - 1.0) / dt[high]
        s[high] -= tt * tt + tt + tt + 1.0

    # 两个共振峰 = 一个口型。级联相加后取包络。
    spec = np.fft.rfft(s)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    resp = (_bandpass_resp(freqs, a * v["formant"], sr, 4.0)
            + 0.7 * _bandpass_resp(freqs, b * v["formant"], sr, 5.0))
    buf = np.fft.irfft(spec * resp, n=n)

    # 5ms 起音、25ms 收尾
    env = np.minimum(1.0, x * 200.0) * np.minimum(1.0, (dur - x) * 40.0)
    out[start:end] += buf * env * v["gain"]


def synth(text: str, out_path: str | Path = "out/bibi.wav", *,
          pitch_hz: float = BASE_PITCH, units_per_second: float = BASE_UPS,
          voice: str = "fish", sample_rate: int = 44100,
          gap: float = 0.22) -> Path:
    """把一句话合成成「哔哔啵啵」的小人说话声，写出 wav 并返回路径。

    pitch_hz:         400 = 不移调；往高整体升调，往低整体降调
    units_per_second: 13 = 默认节奏；越大字越挤，越小越慢
    voice:            'fish' 或 'lumo'
    gap:              句子之间停多少秒
    """
    v = dict(VOICES.get(voice) or VOICES["fish"])

    semis = 12.0 * math.log2(max(1.0, float(pitch_hz)) / BASE_PITCH)
    step = max(0.04, min(0.45, v["step"] * (BASE_UPS / max(0.5, float(units_per_second)))))

    sentences = []
    for raw in _SENT.findall(text or ""):
        tk = syllables(raw)
        if tk:
            sentences.append((raw, tk))
    if not sentences:
        raise ValueError(f"文本里没有可发音的字符: {text!r}")

    sr = int(sample_rate)
    total = sum(len(tk) * step + gap for _, tk in sentences) + 0.4
    out = np.zeros(int(math.ceil(total * sr)), dtype=np.float64)

    t = 0.02
    for raw, tk in sentences:
        ask = bool(re.search(r"[？?]$", raw))
        shout = bool(re.search(r"[！!]", raw))
        sad = bool(re.search(r"(……|\.\.\.|…)$", raw))
        for i, w in enumerate(tk):
            last = i == len(tk) - 1
            hv = hash_of(w)
            m = (v["scale"][hv % len(v["scale"])] + semis
                 + (3.0 if shout else 0.0) - (3.0 if sad else 0.0))
            dur = min(step * v["hold"], v["maxDur"]) + (0.1 if last and (ask or shout or sad) else 0.0)
            glide = 5.0 if (last and ask) else (-4.0 if (last and sad) else (v["fall"] if last else 0.0))
            _render_one(out, sr, t + i * step, m, dur, v, glide, hv)
        t += len(tk) * step + gap

    out = np.tanh(out * 2.4)   # 软限幅，响一点也不破音
    return write_wav(out, out_path, sr)


def write_wav(samples: np.ndarray, out_path: str | Path, sample_rate: int = 44100) -> Path:
    """16 位单声道 wav。"""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(pcm.tobytes())
    return path
