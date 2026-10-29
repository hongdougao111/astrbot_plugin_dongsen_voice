"""文本 → 音节单元序列。

按 Coopanion 的 src/speech/index.ts 思路：
  汉字 → 查 zh_table.json 得 (无调音节, 声调)
  数字 → 中文读法
  英文字母 → 按字母名发音（近似）
  标点 → 记录短语边界（决定静音与语调）

与参考实现的差异：参考实现用 CMU 词典把英文词转 IPA，
这里没有词典，改用「字母名近似」——把每个字母读成最接近的普通话音节。
效果不完美（读的是字母而不是单词），但至少不会静默丢字。
"""
from __future__ import annotations

import json
from pathlib import Path

# 数字的中文读音
DIGITS = ["ling", "yi", "er", "san", "si", "wu", "liu", "qi", "ba", "jiu"]

# 英文字母 → 最接近的普通话音节（按字母名的元音选）
#
# 说明：这是近似方案。参考实现用 CMU 词典查真实读音，
# 这里没有词典，只能按字母名映射。读出来是「字母」而不是「单词」，
# 但比静默丢弃要好——用户至少能听出说了什么。
LETTERS: dict[str, str] = {
    "a": "ei", "b": "bi", "c": "xi", "d": "di", "e": "yi", "f": "ai", "g": "ji",
    "h": "ai", "i": "ai", "j": "jie", "k": "kai", "l": "ai", "m": "en", "n": "en",
    "o": "ou", "p": "pi", "q": "qiu", "r": "a", "s": "ai", "t": "ti", "u": "you",
    "v": "wei", "w": "da", "x": "ai", "y": "wai", "z": "zei",
}

# 弱读字：语速落后时可丢
WEAK_CHARS = set("的了吗呢啊呀吧哦啦么着过")

# 短语分隔标点
MARKS = set(",.!?;:…~，。！？；：、～")
SENTENCE = set("。！？!?\n")


class CharTable:
    """汉字 → (无调音节, 声调)。"""

    def __init__(self, path: str | Path):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.map: dict[str, tuple[str, int]] = {}
        for key, chars in raw.items():
            if not key or not key[-1].isdigit():
                continue
            syl = key[:-1]
            tone = int(key[-1])
            for ch in chars:
                # 先出现的优先（表按常用度排序）
                if ch not in self.map:
                    self.map[ch] = (syl, tone)

    def get(self, ch: str) -> tuple[str, int] | None:
        return self.map.get(ch)

    def __len__(self):
        return len(self.map)


def text_to_units(
    text: str,
    table: CharTable,
    bank_keys: set[str],
) -> list[dict]:
    """把文本转成音节单元列表。

    每个单元: {key, tone, stress, weak, pos, of, end}
      pos/of: 在所属短语中的位置（用于语调）
      end:    该短语的结束标点（决定问句升调等）
    """
    items: list[dict] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        found = False

        # 汉字
        hit = table.get(ch)
        if hit:
            syl, tone = hit
            if syl in bank_keys:
                items.append({
                    "at": i, "key": syl, "tone": tone,
                    "stress": False, "weak": ch in WEAK_CHARS,
                })
            found = True

        # 数字
        if not found and ch.isdigit():
            syl = DIGITS[int(ch)]
            if syl in bank_keys:
                items.append({
                    "at": i, "key": syl, "tone": 0,
                    "stress": False, "weak": False,
                })
            found = True

        # 英文字母：按字母名近似发音
        #
        # 这是「不静默丢字」的兜底。参考实现用 CMU 词典查整词读音，
        # 这里没有词典，只能逐字母映射——读出来是字母不是单词，
        # 但至少用户能听到有内容，而不是说了英文就整段消失。
        if not found and ch.isascii() and ch.isalpha():
            syl = LETTERS.get(ch.lower())
            if syl and syl in bank_keys:
                items.append({
                    "at": i, "key": syl, "tone": 0,
                    "stress": False, "weak": False,
                })
            found = True

        i += 1

    return _phrases(text, items)


def _phrases(text: str, items: list[dict]) -> list[dict]:
    """计算每个单元在短语中的位置，以及短语的结束标点。"""
    items.sort(key=lambda x: x["at"])
    out: list[dict] = []
    start = 0
    m = len(items)

    for u in range(m + 1):
        prev_at = items[u - 1]["at"] if u > 0 else -1
        next_at = items[u]["at"] if u < m else len(text)
        between = text[prev_at + 1:next_at]

        if u < m and not (set(between) & MARKS):
            continue

        if u == m:
            tail = text[prev_at + 1:]
            end = ""
            for c in tail:
                if c in MARKS:
                    end += c
            if not end:
                end = "。"
        else:
            end = "".join(c for c in between if c in MARKS)

        for k in range(start, u):
            out.append({
                **items[k],
                "pos": k - start,
                "of": u - start,
                "end": end,
            })
        start = u

    return out
