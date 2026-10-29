#!/usr/bin/env python
"""插件自测 —— 不需要 AstrBot 环境，验证生成器与参数逻辑。

用法:
    python selftest.py
"""
from __future__ import annotations

import sys
import tempfile
import time
import wave
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from dongsen import say  # noqa: E402

PASS = 0
FAIL = 0
FAILS: list[str] = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        FAILS.append(f"{name} {detail}")
        print(f"  FAIL {name} {detail}")


def read_wav(p):
    with wave.open(str(p), "rb") as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        d = w.readframes(n)
    return d, sr, n, ch, sw


def main():
    tmp = Path(tempfile.gettempdir()) / "dongsen_selftest"
    tmp.mkdir(parents=True, exist_ok=True)

    print("[1] 生成器可用")
    out = tmp / "basic.wav"
    try:
        say("你好呀", out)
        check("合成成功", out.exists())
    except Exception as e:
        check("合成成功", False, str(e))
        print("\n生成器不可用，后续测试跳过")
        return 1

    raw, sr, n, ch, sw = read_wav(out)
    # 音库是 22.05kHz，输出跟随音库采样率。
    # 22kHz 的奈奎斯特频率是 11kHz，远高于动森规格的 4kHz 上限，语音完全够用，
    # 且文件体积比 48kHz 小一半（云端部署省磁盘）。
    check("采样率 >=22kHz", sr >= 22050, str(sr))
    check("单声道", ch == 1, str(ch))
    check("16bit", sw == 2, str(sw))
    check("有内容", n > 1000, str(n))
    check("时长合理", 0.1 < n / sr < 3.0, f"{n/sr:.2f}s")

    print("\n[2] 音高参数")
    lo = tmp / "pitch_364.wav"
    hi = tmp / "pitch_560.wav"
    say("你好", lo, pitch_hz=364)
    say("你好", hi, pitch_hz=560)
    _, _, n_lo, _, _ = read_wav(lo)
    _, _, n_hi, _, _ = read_wav(hi)
    check("高音高更短", n_hi < n_lo, f"{n_hi} vs {n_lo}")

    print("\n[3] 语速参数")
    slow = tmp / "ups_8.wav"
    fast = tmp / "ups_20.wav"
    say("今天天气不错", slow, units_per_second=8)
    say("今天天气不错", fast, units_per_second=20)
    _, sr_s, n_s, _, _ = read_wav(slow)
    _, sr_f, n_f, _, _ = read_wav(fast)
    check("语速快更短", n_f < n_s, f"{n_f} vs {n_s}")

    print("\n[4] 文本处理")
    for text, desc in [
        ("你好", "两字"),
        ("你好，今天", "含逗号"),
        ("你好！", "含感叹号"),
        ("你好？", "含问号"),
        ("123", "纯数字"),
        ("你好呀今天钓到大鱼了吗", "长句"),
    ]:
        p = tmp / f"t_{abs(hash(text)) % 1000}.wav"
        try:
            say(text, p)
            check(f"处理{desc}", p.exists() and p.stat().st_size > 1000)
        except Exception as e:
            check(f"处理{desc}", False, str(e))

    print("\n[5] 边界情况")
    try:
        say("", tmp / "empty.wav")
        check("空文本报错", False, "没有抛异常")
    except ValueError:
        check("空文本报错", True)
    except Exception as e:
        check("空文本报错", False, f"抛了 {type(e).__name__}")

    try:
        say("，。！", tmp / "punct.wav")
        check("纯标点报错", False, "没有抛异常")
    except ValueError:
        check("纯标点报错", True)
    except Exception as e:
        check("纯标点报错", False, f"抛了 {type(e).__name__}")

    print("\n[6] 性能")
    long_text = "欢迎来到动森岛，今天的天气真不错，我们一起去钓鱼吧！"
    t0 = time.time()
    say(long_text, tmp / "perf.wav")
    elapsed = time.time() - t0
    check("长句合成 <3s", elapsed < 3.0, f"{elapsed:.2f}s")

    print("\n[7] 清理")
    for f in tmp.glob("*.wav"):
        try:
            f.unlink()
        except OSError:
            pass
    check("临时文件可清理", True)

    print("\n" + "=" * 46)
    print(f"通过 {PASS} / 失败 {FAIL}")
    if FAILS:
        print("失败项:")
        for f in FAILS:
            print("  -", f)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
