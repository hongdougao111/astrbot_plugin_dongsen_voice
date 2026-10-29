"""动森语音 —— 按 Coopanion 的实现重写。

参考: https://github.com/Pal-AI-Lab/Coopanion
  packages/cortico-world-desktop-pet/scripts/speech-bank/build.py   （音库构建）
  packages/cortico-world-desktop-pet/web/speech.js                   （播放/声调）
  packages/cortico-world-desktop-pet/src/speech/syllable.ts          （音节映射）

核心思想（与纯合成完全不同）：
  1. 音库 = 每个无调普通话音节一个单元，统一音高 364Hz、固定 94ms 发声段
  2. 文本 → 无调音节 → 查库
  3. **音高只靠播放速率改变**（rate = 目标Hz / 364），所以越高越短
  4. 声调 = 速率曲线（8 点插值），幅度只有 TONE_AMOUNT=0.35
  5. 句内音高起伏很小：起点 +0.8 半音，每个音节 -0.06 半音

关键认知：动森语不是「把话说快」，而是「用固定音高的小音节快速连读，
靠微小的速率变化制造语调」。
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# 音库参数（与 build.py 一致）
# ---------------------------------------------------------------------------
BANK_HZ = 364.0          # 音库单元的音高；400Hz 时播放速率 1.1x
UNIT_VOICED_S = 0.094    # 发声段 94ms
CONS_MAX_S = 0.02        # 辅音最长 20ms

# 声调曲线（半音，相对基准），索引 1-5
TONES = {
    1: [0.8, 0.8],          # 阴平
    2: [-0.6, 1.6],         # 阳平
    3: [-1.0, -1.8, -0.6],  # 上声
    4: [1.6, -1.2],         # 去声
    5: [-0.8, -0.8],        # 轻声
}
TONE_AMOUNT = 0.35          # 声调幅度压缩
STRESS_ST = 1.0             # 重音升高半音
GAIN = 0.45

# 标点后的静音（秒）
VOICE_GAP = {
    ",": 0.14, "，": 0.14, "、": 0.14,
    ";": 0.2, "；": 0.2, ":": 0.2, "：": 0.2,
    ".": 0.45, "。": 0.45, "!": 0.5, "！": 0.5,
    "?": 0.5, "？": 0.5, "…": 0.3, "~": 0.1, "～": 0.1,
}

# 弱读字（语速落后时可丢弃）
WEAK_CHARS = set("的了吗呢啊呀吧哦啦么着过")


class SpeechBank:
    """语音库：一个音频文件 + 一份 manifest。

    音库格式（与 Coopanion 一致）：
      manifest: {"hz": 364, "units": {"<音节>": [起始秒, 长度秒]}}
      音频:     所有单元背靠背拼接，单元间有 60ms 静音

    优先加载 .wav，其次 .ogg：
      - 包里带 zh.wav（22.05kHz，3MB）时零依赖，云端部署不需要 ffmpeg
      - 只有 zh.ogg（415KB）时才用 ffmpeg 解码，结果缓存为 zh.wav
    """

    def __init__(self, manifest_path: str | Path, audio_path: str | Path | None = None):
        manifest_path = Path(manifest_path)
        with open(manifest_path, encoding="utf-8") as f:
            meta = json.load(f)
        self.hz = float(meta["hz"])
        self.units: dict[str, tuple[float, float]] = {
            k: (float(v[0]), float(v[1])) for k, v in meta["units"].items()
        }

        if audio_path is None:
            # WAV 优先：避免依赖 ffmpeg
            for ext in (".wav", ".ogg"):
                cand = manifest_path.with_suffix(ext)
                if cand.exists():
                    audio_path = cand
                    break
            else:
                raise FileNotFoundError(
                    f"找不到音库音频：{manifest_path.with_suffix('.wav')} 或 .ogg"
                )

        audio_path = Path(audio_path)
        if audio_path.suffix.lower() == ".ogg":
            wav_path = audio_path.with_suffix(".wav")
            if not wav_path.exists() or wav_path.stat().st_mtime < audio_path.stat().st_mtime:
                self._decode_ogg(audio_path, wav_path)
            audio_path = wav_path

        with wave.open(str(audio_path), "rb") as w:
            self.sr = w.getframerate()
            ch = w.getnchannels()
            raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        data = raw.astype(np.float64) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
        self.audio = data

    @staticmethod
    def _decode_ogg(src: Path, dst: Path) -> None:
        """用 ffmpeg 把 ogg 解成 16bit 单声道 wav。"""
        import shutil
        import subprocess

        ff = shutil.which("ffmpeg")
        if not ff:
            raise RuntimeError("需要 ffmpeg 解码 ogg（或用 --audio 指定 wav）")
        subprocess.run(
            [ff, "-y", "-v", "error", "-i", str(src),
             "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
            check=True,
        )

    def has(self, key: str) -> bool:
        return key in self.units

    def get(self, key: str) -> np.ndarray:
        off, ln = self.units[key]
        a = int(off * self.sr)
        b = int((off + ln) * self.sr)
        return self.audio[a:b]


def tone_curve(tone: int, n_points: int = 8) -> np.ndarray:
    """声调 → n 点速率倍率曲线（半音值，已乘 TONE_AMOUNT）。"""
    pts = TONES.get(tone, [0.0, 0.0])
    out = np.zeros(n_points)
    for k in range(n_points):
        p = k / (n_points - 1)
        x = p * (len(pts) - 1)
        a = int(np.floor(x))
        b = min(len(pts) - 1, a + 1)
        out[k] = (pts[a] + (pts[b] - pts[a]) * (x - a)) * TONE_AMOUNT
    return out


def resample_curve(x: np.ndarray, rates: np.ndarray) -> np.ndarray:
    """按变化的速率曲线重采样。

    等价于 Web Audio 的 playbackRate 曲线：rates 是每个时间点的速率，
    速率越大，输出越短、音高越高。

    实现要点：**必须全向量化**。
    早期版本在 for 循环里逐样本调 np.interp + np.linspace，
    150 字要 2.6 秒（np.linspace 被调用 9.9 万次，占 63% 时间）。
    改成先一次性插值出速率曲线、再 cumsum 求相位，快 10 倍以上。
    """
    n = len(x)
    if n < 2:
        return x
    if len(rates) == 0:
        return x

    mean_rate = float(np.mean(rates))
    if mean_rate <= 1e-9:
        return x
    n_out = max(1, int(round(n / mean_rate)))

    # 一次性把速率曲线插值到 n_out 个点（不再是循环里逐点插值）
    src_u = np.linspace(0.0, 1.0, len(rates))
    dst_u = np.linspace(0.0, 1.0, n_out)
    rate_at = np.interp(dst_u, src_u, rates)

    # 累积相位 = 每个输出样本对应的输入位置
    src = np.concatenate(([0.0], np.cumsum(rate_at[:-1])))
    src = np.clip(src, 0, n - 1)

    i0 = np.floor(src).astype(np.int64)
    i1 = np.minimum(i0 + 1, n - 1)
    frac = src - i0
    return x[i0] * (1 - frac) + x[i1] * frac


def play_unit(
    bank: SpeechBank,
    key: str,
    target_hz: float,
    tone: int = 0,
    stress: bool = False,
    pos: int = 0,
    of: int = 1,
    end: str = "",
    rnd: float = 0.0,
) -> np.ndarray:
    """播放一个音节单元，返回波形。

    严格按 speech.js 的 play() 逻辑：
      st   = 起点偏移（句首 +0.8，每音节 -0.06，随机 ±0.2，感叹 +1，重音 +1）
      问句末尾上升，感叹更响
      声调曲线叠加
      最终 rate = (hz/bank.hz) * 2^((st + tone + bend)/12)
    """
    clip = bank.get(key)
    if len(clip) == 0:
        return np.zeros(0)

    rate_base = target_hz / bank.hz
    is_q = "?" in end or "？" in end
    is_ex = "!" in end or "！" in end
    last = (pos == of - 1)

    st = 0.0
    if pos == 0:
        st += 0.8
    st -= 0.06 * pos
    st += (rnd - 0.5) * 0.4
    if is_ex:
        st += 1.0
    if stress:
        st += STRESS_ST

    bend = 0.0
    if is_q and pos == of - 2:
        st += 1.5
    if is_q and last:
        st += 2.0
        bend = 3.0
    if "…" in end and last:
        st -= 0.8

    tc = tone_curve(tone, 8) if tone else np.zeros(8)

    # 每个输出点的速率
    n_pts = 16
    rates = np.zeros(n_pts)
    for k in range(n_pts):
        p = k / (n_pts - 1)
        ts = np.interp(p, np.linspace(0, 1, len(tc)), tc)
        semis = st + ts + bend * p
        rates[k] = rate_base * 2.0 ** (semis / 12.0)

    out = resample_curve(clip, rates)
    gain = GAIN * (1.26 if is_ex else 1.0)
    return out * gain


MAX_LAG = 1.0   # 落后超过 1 秒：丢弱读字；超过 2 秒：只保留短语末两字


def render_speech(
    units: list[dict],
    bank: SpeechBank,
    out_path: str | Path,
    pitch_hz: float = 400.0,
    units_per_second: float = 13.0,
    seed: int = 1,
    max_lag: float = MAX_LAG,
) -> Path:
    """把音节单元序列渲染成完整音频。

    units: [{'key','tone','stress','weak','pos','of','end'}]

    节奏按 VoiceClock 排布：相邻单元至少间隔 1/ups 秒。
    若某个单元因排布而落后「应有时间」太多，按参考实现丢弃：
      落后 > max_lag 且是弱读字  → 丢
      落后 > 2*max_lag 且不是短语末两字 → 丢
    这是为了避免长句末尾语音拖得太久，听感上像「跟不上」。
    """
    sr = bank.sr
    rnd_state = seed

    def random():
        nonlocal rnd_state
        rnd_state = (rnd_state * 16807) % 2147483647
        return rnd_state / 2147483647

    pieces: list[np.ndarray] = []
    last_start = -1e9
    last_end = 0.0
    free = 0.0
    gap = 0.0

    # 「应有时间」：按每秒 ups 个单元线性推进
    expected = 0.0
    cursor = 0          # 已写入的样本总数
    dropped = 0

    for u in units:
        if not bank.has(u["key"]):
            continue
        rate = pitch_hz / bank.hz
        clip_len = bank.units[u["key"]][1] / rate

        t = max(last_start + 1.0 / units_per_second, free)
        lag = t - expected
        is_final = u.get("pos", 0) >= u.get("of", 1) - 2

        if max_lag > 0 and not is_final:
            if lag > 2 * max_lag or (lag > max_lag and u.get("weak", False)):
                dropped += 1
                expected += 1.0 / units_per_second
                continue

        start_sample = int(t * sr)
        wav = play_unit(
            bank, u["key"], pitch_hz,
            tone=u.get("tone", 0), stress=u.get("stress", False),
            pos=u.get("pos", 0), of=u.get("of", 1),
            end=u.get("end", ""), rnd=random(),
        )

        # 累计长度用游标追踪，避免每轮都 sum() 造成 O(n²)
        if start_sample > cursor:
            pieces.append(np.zeros(start_sample - cursor))
            cursor = start_sample
        pieces.append(wav)
        cursor += len(wav)

        last_start = t
        last_end = t + len(wav) / sr
        free = last_end
        expected += 1.0 / units_per_second

        gap = 0.0
        # 只有短语最后一个单元才加标点静音
        if u.get("pos", 0) >= u.get("of", 1) - 1:
            for ch, g in VOICE_GAP.items():
                if ch in u.get("end", ""):
                    gap = max(gap, g)
        if gap:
            free = last_end + gap
            expected = free

    if not pieces:
        return Path(out_path)

    audio = np.concatenate(pieces)
    m = np.abs(audio).max()
    if m > 1e-9:
        audio = audio / m * 0.9

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path
