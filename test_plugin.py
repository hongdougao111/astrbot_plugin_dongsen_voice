#!/usr/bin/env python
"""插件逻辑测试 —— 用假对象模拟 AstrBot，验证配置、概率、钩子。

不需要安装 AstrBot。

用法:
    python test_plugin.py
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

HERE = Path(__file__).parent

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


# ---------------------------------------------------------------------------
# 伪造 astrbot 模块
# ---------------------------------------------------------------------------
def install_fake_astrbot():
    class BaseMessageComponent:
        pass

    class Plain(BaseMessageComponent):
        def __init__(self, text=""):
            self.text = text

    class Image(BaseMessageComponent):
        pass

    class Record(BaseMessageComponent):
        def __init__(self, file=""):
            self.file = file

        @staticmethod
        def fromFileSystem(path, **_):
            return Record(file=f"file://{path}")

    comp_mod = types.ModuleType("astrbot.api.message_components")
    comp_mod.Plain = Plain
    comp_mod.Image = Image
    comp_mod.Record = Record
    comp_mod.BaseMessageComponent = BaseMessageComponent

    class FakeConfig(dict):
        """模拟 AstrBotConfig：继承 dict，带 save_config。"""

        def save_config(self):
            pass

    api_mod = types.ModuleType("astrbot.api")
    api_mod.message_components = comp_mod
    api_mod.AstrBotConfig = FakeConfig
    api_mod.logger = types.SimpleNamespace(
        error=lambda *a, **k: None,
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
    )

    ev_mod = types.ModuleType("astrbot.api.event")

    class _Filter:
        @staticmethod
        def command(*a, **k):
            def deco(f):
                return f
            return deco

        @staticmethod
        def on_decorating_result(*a, **k):
            def deco(f):
                return f
            return deco

    ev_mod.filter = _Filter
    ev_mod.AstrMessageEvent = object

    star_mod = types.ModuleType("astrbot.api.star")

    class Star:
        def __init__(self, context=None):
            pass

    def register(*a, **k):
        def deco(cls):
            return cls
        return deco

    star_mod.Star = Star
    star_mod.Context = object
    star_mod.register = register

    sys.modules["astrbot"] = types.ModuleType("astrbot")
    sys.modules["astrbot.api"] = api_mod
    sys.modules["astrbot.api.message_components"] = comp_mod
    sys.modules["astrbot.api.event"] = ev_mod
    sys.modules["astrbot.api.star"] = star_mod
    return Plain, Image, Record, FakeConfig


class FakeResult:
    def __init__(self, chain, ctype="LLM_RESULT"):
        self.chain = chain
        self.result_content_type = types.SimpleNamespace(name=ctype)


class FakeEvent:
    def __init__(self, chain, ctype="LLM_RESULT", session="test:group:1"):
        self._result = FakeResult(chain, ctype)
        self.unified_msg_origin = session

    def get_result(self):
        return self._result


def main():
    Plain, Image, Record, FakeConfig = install_fake_astrbot()
    sys.path.insert(0, str(HERE))

    import main as plugin_main

    P = plugin_main.DongsenVoicePlugin

    # ------------------------------------------------------------------
    print("[1] 配置 Schema")
    schema_path = HERE / "_conf_schema.json"
    check("_conf_schema.json 存在", schema_path.exists())
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for key in ("enable_auto", "auto_probability", "pitch_hz",
                "units_per_second", "max_chars", "min_chars"):
        check(f"Schema 含 {key}", key in schema, str(list(schema)[:5]))

    # 每个配置项必须有 type
    missing_type = [k for k, v in schema.items() if "type" not in v]
    check("所有项都有 type", not missing_type, str(missing_type))

    # slider 项必须有 min/max
    bad_slider = []
    for k, v in schema.items():
        if "slider" in v:
            s = v["slider"]
            if "min" not in s or "max" not in s:
                bad_slider.append(k)
    check("slider 配置完整", not bad_slider, str(bad_slider))

    # 默认值在 slider 范围内
    bad_default = []
    for k, v in schema.items():
        if "slider" in v and "default" in v:
            s = v["slider"]
            if not (s["min"] <= v["default"] <= s["max"]):
                bad_default.append(k)
    check("默认值在范围内", not bad_default, str(bad_default))

    # 概率默认应为 100
    check("概率默认 100", schema["auto_probability"]["default"] == 100)
    check("自动默认关闭", schema["enable_auto"]["default"] is False)

    # ------------------------------------------------------------------
    print("\n[2] 配置读取")
    cfg = FakeConfig({
        "enable_auto": True,
        "auto_probability": 50,
        "pitch_hz": 480,
        "units_per_second": 18,
        "max_chars": 100,
        "min_chars": 3,
        "per_session_settings": True,
        "send_text_too": False,
        "cleanup_minutes": 10,
    })
    p = P(context=None, config=cfg)
    s = "test:group:1"

    check("读 enable_auto", p._auto_on() is True)
    check("读概率", p._prob() == 50)
    check("读音高", p._pitch(s) == 480.0)
    check("读语速", p._ups(s) == 18.0)

    # 无配置时的默认值
    p0 = P(context=None, config=None)
    check("无配置-自动关", p0._auto_on() is False)
    check("无配置-概率100", p0._prob() == 100)
    check("无配置-音高400", p0._pitch(s) == 400.0)
    check("无配置-语速13", p0._ups(s) == 13.0)

    # ------------------------------------------------------------------
    print("\n[3] 配置越界保护")
    bad_cfg = FakeConfig({
        "enable_auto": True,
        "auto_probability": 999,     # 越界
        "pitch_hz": 9999,            # 越界
        "units_per_second": 0,       # 越界
        "max_chars": 150,
        "min_chars": 2,
        "per_session_settings": True,
    })
    pb = P(context=None, config=bad_cfg)
    check("概率钳到 100", pb._prob() == 100, str(pb._prob()))
    check("音高钳到 700", pb._pitch(s) == 700.0, str(pb._pitch(s)))
    check("语速钳到 5", pb._ups(s) == 5.0, str(pb._ups(s)))

    # 类型错误
    weird_cfg = FakeConfig({
        "pitch_hz": "abc",
        "units_per_second": None,
        "auto_probability": "x",
    })
    pw = P(context=None, config=weird_cfg)
    check("脏数据回退音高", pw._pitch(s) == 400.0, str(pw._pitch(s)))
    check("脏数据回退语速", pw._ups(s) == 13.0, str(pw._ups(s)))
    check("脏数据回退概率", pw._prob() == 100, str(pw._prob()))

    # ------------------------------------------------------------------
    print("\n[4] 会话级覆盖")
    check("初始无覆盖", p._pitch(s) == 480.0)
    p._session_pitch[s] = 520.0
    check("覆盖生效", p._pitch(s) == 520.0)
    check("其他会话不受影响", p._pitch("other:group:9") == 480.0)

    # 关闭会话调整时覆盖失效
    cfg["per_session_settings"] = False
    check("关闭后忽略覆盖", p._pitch(s) == 480.0, str(p._pitch(s)))
    cfg["per_session_settings"] = True
    p._session_pitch.pop(s, None)

    # ------------------------------------------------------------------
    print("\n[5] 文本过滤")
    p._session_pitch.clear()
    cases = [
        ("你好呀", True, "正常中文"),
        ("Hello", True, "英文"),
        ("123", True, "数字"),
        ("a", False, "低于 min_chars=3"),
        ("你好", False, "刚好 2 字 < 3"),
        ("你好呀", True, "刚好 3 字"),
        ("", False, "空"),
        ("！？。", False, "纯标点"),
        ("😀😀😀", False, "纯表情"),
        ("字" * 101, False, "超过 max_chars=100"),
    ]
    for text, expect, desc in cases:
        got = p._should_convert(text)
        check(desc, got == expect, f"{text[:15]!r} 实际 {got}")

    # ------------------------------------------------------------------
    print("\n[6] 消息类型判断")
    for name, expect in [
        ("LLM_RESULT", True),
        ("STREAMING_FINISH", True),
        ("STREAMING_RESULT", False),
        ("GENERAL_RESULT", False),
        ("AGENT_RUNNER_ERROR", False),
    ]:
        r = FakeResult([], name)
        check(f"{name} -> {expect}", P._is_model_output(r) == expect)

    # ------------------------------------------------------------------
    print("\n[7] 钩子行为")
    import asyncio

    # 自动关闭
    cfg["enable_auto"] = False
    ev = FakeEvent([Plain("你好呀今天天气不错")])
    asyncio.run(p.auto_voice(ev))
    check("关闭时不转换", isinstance(ev.get_result().chain[0], Plain))

    # 自动开启 + LLM 回复
    cfg["enable_auto"] = True
    cfg["auto_probability"] = 100
    ev2 = FakeEvent([Plain("你好呀今天天气不错")])
    asyncio.run(p.auto_voice(ev2))
    check("开启后转语音", isinstance(ev2.get_result().chain[0], Record),
          str([type(c).__name__ for c in ev2.get_result().chain]))

    # 指令回复不转
    ev3 = FakeEvent([Plain("你好呀今天天气不错")], ctype="GENERAL_RESULT")
    asyncio.run(p.auto_voice(ev3))
    check("指令回复不转", isinstance(ev3.get_result().chain[0], Plain))

    # 保留图片
    ev4 = FakeEvent([Plain("看这个图片"), Image()])
    asyncio.run(p.auto_voice(ev4))
    chain4 = ev4.get_result().chain
    check("语音在前", isinstance(chain4[0], Record))
    check("图片保留", any(isinstance(c, Image) for c in chain4))

    # send_text_too
    cfg["send_text_too"] = True
    ev5 = FakeEvent([Plain("你好呀今天天气不错")])
    asyncio.run(p.auto_voice(ev5))
    chain5 = ev5.get_result().chain
    check("同时发文字", any(isinstance(c, Plain) for c in chain5),
          str([type(c).__name__ for c in chain5]))
    cfg["send_text_too"] = False

    # ------------------------------------------------------------------
    print("\n[8] 概率统计")
    cfg["auto_probability"] = 1
    hits = 0
    for _ in range(100):
        e = FakeEvent([Plain("你好呀今天天气不错")])
        asyncio.run(p.auto_voice(e))
        if isinstance(e.get_result().chain[0], Record):
            hits += 1
    check("1% 概率 100 次命中 0-8", hits <= 8, f"命中 {hits}")

    cfg["auto_probability"] = 100
    hits2 = 0
    for _ in range(20):
        e = FakeEvent([Plain("你好呀今天天气不错")])
        asyncio.run(p.auto_voice(e))
        if isinstance(e.get_result().chain[0], Record):
            hits2 += 1
    check("100% 概率 20 次全中", hits2 == 20, f"命中 {hits2}")

    # ------------------------------------------------------------------
    print("\n[9] 零依赖（无 ffmpeg）")
    import shutil
    _orig_which = shutil.which
    shutil.which = lambda name, *a, **k: None if name == "ffmpeg" else _orig_which(name, *a, **k)
    try:
        from dongsen.coop import SpeechBank
        b = SpeechBank(HERE / "dongsen" / "data" / "zh.json")
        check("无 ffmpeg 可加载", len(b.units) > 300, str(len(b.units)))
        check("音库采样率 22050", b.sr == 22050, str(b.sr))
    except Exception as e:
        check("无 ffmpeg 可加载", False, str(e))
    finally:
        shutil.which = _orig_which

    # ------------------------------------------------------------------
    print("\n[10] 英文处理（曾经静默丢字的 BUG）")
    from dongsen import load_bank, load_table
    from dongsen.text2units import text_to_units

    bank = load_bank()
    table = load_table()
    keys = set(bank.units)

    for txt, desc in [
        ("hello", "纯英文"),
        ("OK", "大写英文"),
        ("Python", "混合大小写"),
        ("你好ABC", "中英混排"),
        ("abc123", "英文+数字"),
        ("I love you", "英文短句"),
    ]:
        u = text_to_units(txt, table, keys)
        check(f"{desc} 有音节", len(u) > 0, f"{txt!r} -> {len(u)}")

    # 中英混排时英文不能被吞掉
    u_mix = text_to_units("你好ABC", table, keys)
    check("混排不丢字", len(u_mix) == 5, f"实际 {len(u_mix)} 个音节")

    # ------------------------------------------------------------------
    print("\n[11] 性能（向量化后）")
    import time as _time
    t0 = _time.time()
    p._session_pitch.clear()
    long_txt = ("你好今天天气不错" * 20)[:150]
    asyncio.run(p._synthesize(long_txt, s))
    elapsed = _time.time() - t0
    check("150 字 <1s", elapsed < 1.0, f"{elapsed:.3f}s")

    # ------------------------------------------------------------------
    print("\n[12] 临时文件名唯一性")
    import re
    paths = set()
    for _ in range(5):
        out = asyncio.run(p._synthesize("你好呀今天天气不错", s))
        if out:
            paths.add(out.name)
    check("5 次合成文件名不同", len(paths) == 5, f"实际 {len(paths)} 个")
    # 文件名应是 uuid 格式，不含 hash 痕迹
    if paths:
        sample = list(paths)[0]
        check("文件名格式正确", re.match(r"^ds_[0-9a-f]{16}\.wav$", sample) is not None,
              sample)

    # ------------------------------------------------------------------
    print("\n[13] 空音频防护")
    # 纯标点：_should_convert 应拦下
    check("纯标点不转", p._should_convert("，。！？") is False)
    # 直接调 say 应抛 ValueError
    try:
        from dongsen import say as _say
        import tempfile as _tf
        _say("，。！", Path(_tf.gettempdir()) / "empty_test.wav")
        check("纯标点合成报错", False, "没有抛异常")
    except ValueError:
        check("纯标点合成报错", True)
    except Exception as e:
        check("纯标点合成报错", False, f"抛了 {type(e).__name__}")

    # ------------------------------------------------------------------
    print("\n[14] 多音字词组")
    from dongsen import phrases as ph

    st = ph.stats()
    check("词表规模 >300", st["phrase_count"] > 300, str(st["phrase_count"]))
    check("最长词条 >=3", st["longest"] >= 3, str(st["longest"]))

    # 关键多音字必须读对
    polyphone_cases = [
        ("银行", ["yin2", "hang2"], "银行 háng"),
        ("音乐", ["yin1", "yue4"], "音乐 yuè"),
        ("重新", ["chong2", "xin1"], "重新 chóng"),
        ("了解", ["liao3", "jie3"], "了解 liǎo"),
        ("长大", ["zhang3", "da4"], "长大 zhǎng"),
        ("快乐", ["kuai4", "le4"], "快乐 lè"),
        ("处理", ["chu3", "li3"], "处理 chǔ"),
        ("数量", ["shu4", "liang4"], "数量 liàng"),
        ("行业", ["hang2", "ye4"], "行业 háng"),
        ("觉得", ["jue2", "de5"], "觉得 jué"),
    ]
    for word, expect, desc in polyphone_cases:
        u = text_to_units(word, table, keys)
        got = [x["key"] + str(x["tone"] if x["tone"] else 5) for x in u]
        check(desc, got == expect, f"{word} -> {got}")

    # 词组在句中要正确匹配
    u_sent = text_to_units("我去银行听音乐", table, keys)
    syls = [x["key"] for x in u_sent]
    check("句中词组匹配", "hang" in syls and "yue" in syls, str(syls))

    # 部分匹配不能误伤：单字「银」应回落
    u_single = text_to_units("银", table, keys)
    check("单字回落正常", len(u_single) == 1 and u_single[0]["key"] == "yin",
          str([x["key"] for x in u_single]))

    # 最长优先：「音乐家」应先匹配「音乐」
    u_long = text_to_units("音乐家", table, keys)
    check("最长优先", [x["key"] for x in u_long] == ["yin", "yue", "jia"],
          str([x["key"] for x in u_long]))

    # 词组不能破坏长度：合成结果音节数应等于词长
    for word in ["银行", "重新", "了解", "音乐会"]:
        u = text_to_units(word, table, keys)
        check(f"{word} 音节数匹配", len(u) == len(word), f"{len(u)} vs {len(word)}")

    # ------------------------------------------------------------------
    print("\n[15] 启动自检")
    check("有自检方法", hasattr(P, "_self_check"))
    check("自检结果已缓存", hasattr(p, "_diag"))

    diag = getattr(p, "_diag", {})
    check("diag 有 ok 字段", "ok" in diag, str(diag.keys()))
    check("diag 有 problems 字段", "problems" in diag, str(diag.keys()))

    ok_list = diag.get("ok", [])
    prob_list = diag.get("problems", [])
    check("自检无问题", len(prob_list) == 0, str(prob_list))
    check("自检有通过项", len(ok_list) >= 3, str(ok_list))

    # 关键项应在 ok 里
    joined = " ".join(str(x) for x in ok_list)
    check("检查了音库", "音库" in joined, joined[:80])
    check("检查了字表", "字表" in joined, joined[:80])
    check("检查了钩子", "钩子" in joined, joined[:80])
    check("检查了合成", "合成" in joined, joined[:80])

    print("\n[16] 诊断指令")
    check("有诊断指令", hasattr(P, "diagnose"))

    # 内存优化：音库应是 float32
    from dongsen import load_bank as _lb

    _b = _lb()
    check("音库 float32", str(_b.audio.dtype) == "float32", str(_b.audio.dtype))
    mem_mb = _b.audio.nbytes / 1024 / 1024
    check("内存 <8MB", mem_mb < 8, f"{mem_mb:.1f}MB")

    # ------------------------------------------------------------------
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
