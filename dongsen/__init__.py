"""动森语音生成器 —— 顶层接口。

    from dongsen import say
    say("你好呀，今天钓到大鱼了吗", "out/hello.wav")

实现基于 Coopanion 的动森语音方案：
  https://github.com/Pal-AI-Lab/Coopanion

核心：音库 = 每个无调普通话音节一个单元（统一 364Hz、94ms 发声段），
文本按字查表得音节，播放时只靠速率改变音高。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .coop import SpeechBank, render_speech
from .text2units import CharTable, text_to_units

__all__ = ["say", "say_units", "load_bank", "load_table", "DATA_DIR"]

DATA_DIR = Path(__file__).parent / "data"

# 默认音高（Hz）。364 是音库原生音高，400 是动森的实际音域。
DEFAULT_PITCH = 400.0
DEFAULT_UPS = 13.0


@lru_cache(maxsize=1)
def load_bank(manifest: str | Path | None = None) -> SpeechBank:
    """加载语音库（进程内只加载一次）。"""
    path = Path(manifest) if manifest else DATA_DIR / "zh.json"
    return SpeechBank(path)


@lru_cache(maxsize=1)
def load_table(path: str | Path | None = None) -> CharTable:
    """加载汉字→音节表。"""
    return CharTable(Path(path) if path else DATA_DIR / "zh_table.json")


def say(
    text: str,
    out_path: str | Path = "out/dongsen.wav",
    pitch_hz: float = DEFAULT_PITCH,
    units_per_second: float = DEFAULT_UPS,
    seed: int = 1,
    bank: SpeechBank | None = None,
    table: CharTable | None = None,
) -> Path:
    """把中文文本合成为动森风格语音。

    pitch_hz:         音高，364=音库原音，400=动森音域，越高越短越尖
    units_per_second: 每秒最多起几个音节，13 是动森的语速
    seed:             随机种子（影响句内音高的细微起伏）
    """
    bank = bank or load_bank()
    table = table or load_table()

    units = text_to_units(text, table, set(bank.units))
    if not units:
        raise ValueError(f"文本里没有可发音的字符: {text!r}")

    return render_speech(
        units, bank, out_path,
        pitch_hz=pitch_hz,
        units_per_second=units_per_second,
        seed=seed,
    )


def say_units(
    text: str,
    out_path: str | Path = "out/dongsen.wav",
    **kwargs,
) -> tuple[Path, list[dict]]:
    """同 say()，但额外返回音节单元列表（便于调试）。"""
    bank = kwargs.pop("bank", None) or load_bank()
    table = kwargs.pop("table", None) or load_table()
    units = text_to_units(text, table, set(bank.units))
    path = render_speech(units, bank, out_path, **kwargs)
    return path, units
