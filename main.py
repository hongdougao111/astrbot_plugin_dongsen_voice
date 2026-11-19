"""动森语音插件 —— 让 Bot 用动森腔调说话。

两种模式：
  1. 自动模式：Bot 的回复按设定概率转成语音（管理面板配置）
  2. 手动模式：/动森 指令合成任意文字

云端部署友好：
  - 音库自带 WAV 版本，不依赖 ffmpeg
  - 临时文件按时长自动清理
  - 所有参数在 WebUI 管理面板可视化调整

指令（可用 per_session_settings 关闭）：
    /动森 你好呀              合成并发送语音
    /动森音高 440              本群音高
    /动森语速 15               本群语速
    /动森状态                  查看当前设置
    /动森重置                  恢复管理面板配置

实现基于 Coopanion 的音库方案：
    https://github.com/Pal-AI-Lab/Coopanion
"""
from __future__ import annotations

import asyncio
import random
import sys
import tempfile
import time
from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

# 插件自带的生成器
_PLUGIN_DIR = Path(__file__).parent
sys.path.insert(0, str(_PLUGIN_DIR))

from dongsen import say, say_engine  # noqa: E402

# 硬边界（防止配置填错导致崩溃）
PITCH_MIN, PITCH_MAX = 300.0, 700.0
UPS_MIN, UPS_MAX = 5.0, 25.0
TEXT_HARD_MAX = 300

# 两套引擎。关掉一个，声线自动落到另一个；两个都关就不发语音。
ENGINE_DONGSEN = "dongsen"
ENGINE_BIBI = "bibi"
ENGINE_LABELS = {ENGINE_DONGSEN: "动森", ENGINE_BIBI: "哔哔啵啵"}
ENGINE_KEYS = {ENGINE_DONGSEN: "enable_dongsen", ENGINE_BIBI: "enable_bibi"}

# 声线 → 所属引擎
VOICE_ENGINE = {"dongsen": ENGINE_DONGSEN, "fish": ENGINE_BIBI, "lumo": ENGINE_BIBI}

# 可选声线。mix = 在开着的引擎里随机挑，两个引擎都用得上。
VOICES = ("dongsen", "fish", "lumo", "mix")
VOICE_LABELS = {"dongsen": "动森腔", "fish": "大肥鱼", "lumo": "路墨", "mix": "混着来"}

# 配置默认值（与 _conf_schema.json 保持一致）
DEFAULTS = {
    "enable_auto": False,
    "enable_dongsen": True,
    "enable_bibi": True,
    "voice": "mix",
    "auto_probability": 100,
    "pitch_hz": 400,
    "units_per_second": 13,
    "max_chars": 150,
    "min_chars": 2,
    "per_session_settings": True,
    "send_text_too": False,
    "cleanup_minutes": 10,
}


@register(
    "astrbot_plugin_dongsen_voice",
    "hongdougao111",
    "把 Bot 的回复变成动森风格语音",
    "1.6.0",
)
class DongsenVoicePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config
        # 会话级覆盖（指令设置的临时参数）
        self._session_pitch: dict[str, float] = {}
        self._session_ups: dict[str, float] = {}
        self._session_voice: dict[str, str] = {}
        self._tmpdir = Path(tempfile.gettempdir()) / "astrbot_dongsen"
        self._tmpdir.mkdir(parents=True, exist_ok=True)
        self._last_cleanup = 0.0
        # 自检结果，供 /动森诊断 使用
        self._diag: dict[str, object] = {}
        self._self_check()

    # ---------- 启动自检 ----------

    def _self_check(self) -> None:
        """启动时检查运行环境，把结果写日志并缓存。

        为什么需要：如果 AstrBot 版本变化导致钩子失效或音库缺失，
        插件会**静默不工作**——用户看到的现象是"没反应"，
        但日志里什么都没有，极难排查。这里主动探一遍。
        """
        problems: list[str] = []
        ok: list[str] = []

        # 1. 音库
        try:
            from dongsen import load_bank

            bank = load_bank()
            ok.append(f"音库 {len(bank.units)} 单元 / {bank.sr}Hz / {bank.audio.nbytes // 1024 // 1024}MB")
        except Exception as e:
            problems.append(f"音库加载失败: {e}")
            bank = None

        # 2. 字表
        try:
            from dongsen import load_table

            table = load_table()
            ok.append(f"字表 {len(table)} 字")
        except Exception as e:
            problems.append(f"字表加载失败: {e}")
            table = None

        # 3. 钩子注册（能否找到 on_decorating_result）
        try:
            hook = getattr(self, "auto_voice", None)
            if hook is None:
                problems.append("auto_voice 钩子未注册")
            elif not callable(hook):
                problems.append("auto_voice 不是可调用对象")
            else:
                ok.append("钩子已注册")
        except Exception as e:
            problems.append(f"钩子检查异常: {e}")

        # 4. ResultContentType 枚举（版本兼容性）
        try:
            from astrbot.core.message.message_event_result import ResultContentType

            names = {x.name for x in ResultContentType}
            needed = {"LLM_RESULT", "STREAMING_FINISH"}
            missing = needed - names
            if missing:
                problems.append(f"ResultContentType 缺字段: {missing}（版本不兼容）")
            else:
                ok.append(f"消息类型枚举 {len(names)} 项")
        except ImportError:
            # 不同版本路径可能不同，不算致命
            ok.append("消息类型枚举路径不同（可能是新版 AstrBot）")
        except Exception as e:
            problems.append(f"枚举检查异常: {e}")

        # 5. 合成能力（两套引擎各真正跑一次，按开关来）
        on = self._engines_on()
        if not on:
            problems.append("两套引擎都关了（enable_dongsen / enable_bibi 都是关）")
        elif ENGINE_DONGSEN not in on:
            ok.append("动森引擎已关闭，跳过")
        elif bank is not None and table is not None:
            try:
                import tempfile as _tf

                probe = Path(_tf.gettempdir()) / "astrbot_dongsen_probe.wav"
                say("测试", probe, pitch_hz=400, units_per_second=13)
                size = probe.stat().st_size
                probe.unlink(missing_ok=True)
                if size > 1000:
                    ok.append(f"动森合成正常（{size // 1024}KB）")
                else:
                    problems.append(f"动森合成结果过小: {size} bytes")
            except Exception as e:
                problems.append(f"动森合成失败: {e}")

        if ENGINE_BIBI in on:
            probe = Path(tempfile.gettempdir()) / "astrbot_bibi_probe.wav"
            try:
                say_engine("测试", probe, engine=ENGINE_BIBI, voice="fish")
                size = probe.stat().st_size
                probe.unlink(missing_ok=True)
                if size > 1000:
                    ok.append(f"哔哔啵啵合成正常（{size // 1024}KB）")
                else:
                    problems.append(f"哔哔啵啵合成结果过小: {size} bytes")
            except Exception as e:
                problems.append(f"哔哔啵啵合成失败: {e}")

        self._diag = {"ok": ok, "problems": problems}

        if problems:
            logger.error(
                "[dongsen] 自检发现问题：\n  - " + "\n  - ".join(problems)
                + "\n  （插件可能无法正常工作，请检查依赖与版本）"
            )
        else:
            logger.info("[dongsen] 自检通过：" + "；".join(ok))

    # ---------- 配置读取 ----------

    def _cfg(self, key: str):
        """读配置，带回退默认值。"""
        default = DEFAULTS.get(key)
        if self.config is None:
            return default
        try:
            val = self.config.get(key, default)
        except Exception:
            return default
        if val is None:
            return default
        return val

    def _pitch(self, session: str) -> float:
        """音高：会话覆盖优先，其次配置。"""
        if self._cfg("per_session_settings") and session in self._session_pitch:
            return self._session_pitch[session]
        try:
            v = float(self._cfg("pitch_hz"))
        except (TypeError, ValueError):
            v = 400.0
        return max(PITCH_MIN, min(PITCH_MAX, v))

    def _ups(self, session: str) -> float:
        """语速：会话覆盖优先，其次配置。"""
        if self._cfg("per_session_settings") and session in self._session_ups:
            return self._session_ups[session]
        try:
            v = float(self._cfg("units_per_second"))
        except (TypeError, ValueError):
            v = 13.0
        return max(UPS_MIN, min(UPS_MAX, v))

    def _voice(self, session: str) -> str:
        """配置里的声线（不含会话覆盖），认不出的按 mix 处理。"""
        v = str(self._cfg("voice") or "mix").strip().lower()
        return v if v in VOICES else "mix"

    # ---------- 引擎开关 ----------

    def _engine_on(self, engine: str) -> bool:
        """某一套引擎是否启用。认不出的引擎名一律当关。"""
        key = ENGINE_KEYS.get(engine)
        return bool(self._cfg(key)) if key else False

    def _engines_on(self) -> list[str]:
        """开着的引擎，按优先级：动森在前，哔哔啵啵在后。"""
        return [e for e in (ENGINE_DONGSEN, ENGINE_BIBI) if self._engine_on(e)]

    def _any_engine(self) -> bool:
        return bool(self._engines_on())

    def _engines_text(self) -> str:
        """「动森+哔哔啵啵」这种人读的开关摘要。"""
        on = self._engines_on()
        if not on:
            return "全关"
        if len(on) == 2:
            return "动森+哔哔啵啵"
        return ENGINE_LABELS[on[0]] + "（另一套已关）"

    def _pick(self, session: str) -> tuple[str, str]:
        """定下这一次用哪套引擎、哪条声线，返回 (引擎, 声线)；两套都关返回 ("", "")。

        规则按顺序：
          1. 声线所属的引擎开着 → 就用它（mix 在开着的引擎里抽）
          2. 声线那套关了 → 换到还开着的那套，声线跟着换成它的默认
          3. 两套都关 → ("", "")
        """
        on = self._engines_on()
        if not on:
            return "", ""
        v = self._session_voice.get(session) if self._cfg("per_session_settings") else None
        v = str(v or self._voice(session)).strip().lower()
        if v not in VOICE_ENGINE and v != "mix":
            v = "mix"

        if v == "mix":
            engine = random.choice(on)
        else:
            engine = VOICE_ENGINE[v]
            if engine not in on:
                engine = on[0]

        if engine == ENGINE_DONGSEN:
            return engine, "dongsen"
        if v in ("fish", "lumo"):
            return engine, v
        return engine, random.choice(("fish", "lumo"))

    def _auto_on(self) -> bool:
        return bool(self._cfg("enable_auto"))

    def _prob(self) -> int:
        try:
            v = int(self._cfg("auto_probability"))
        except (TypeError, ValueError):
            v = 100
        return max(1, min(100, v))

    # ---------- 工具 ----------

    def _cleanup(self, force: bool = False):
        """清理过期临时文件。每分钟最多跑一次，避免频繁扫盘。"""
        now = time.time()
        if not force and now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        try:
            minutes = float(self._cfg("cleanup_minutes"))
        except (TypeError, ValueError):
            minutes = 10.0
        ttl = max(60.0, minutes * 60.0)
        try:
            for f in self._tmpdir.glob("*.wav"):
                try:
                    if now - f.stat().st_mtime > ttl:
                        f.unlink()
                except OSError:
                    pass
        except OSError as e:
            logger.warning(f"[dongsen] 清理临时文件失败: {e}")

    async def _synthesize(self, text: str, session: str) -> Path | None:
        """合成语音，返回文件路径。失败返回 None。

        文件名用 uuid，不用 hash()：
          - hash() 受 PYTHONHASHSEED 影响，多进程部署时不同进程结果不同
          - hash() 有碰撞可能，两条不同文本可能覆盖同一文件
        """
        import uuid

        out = self._tmpdir / f"ds_{uuid.uuid4().hex[:16]}.wav"
        engine, voice = self._pick(session)
        if not engine:
            # 两套都关：不发语音，也不算失败
            return None

        # 先用挑中的那套；它挂了（音库缺文件、numpy 版本不对…）
        # 就换还开着的那套再试一次，两套都不成才算真失败。
        tries = [(engine, voice)]
        rest = [e for e in self._engines_on() if e != engine]
        if rest:
            tries.append((rest[0], "dongsen" if rest[0] == ENGINE_DONGSEN else "fish"))

        last_err: Exception | None = None
        for eng, voc in tries:
            try:
                await asyncio.to_thread(
                    say_engine, text, out,
                    engine=eng,
                    voice=voc,
                    pitch_hz=self._pitch(session),
                    units_per_second=self._ups(session),
                )
                if out.exists() and out.stat().st_size >= 1000:
                    if (eng, voc) != (engine, voice):
                        logger.info(f"[dongsen] {ENGINE_LABELS[engine]} 没合成出来，"
                                    f"改用 {ENGINE_LABELS[eng]}（{voc}）")
                    return out
                last_err = RuntimeError(f"{eng} 合成结果为空或过小")
            except Exception as e:  # noqa: BLE001 — 挂哪套都要接着试另一套
                last_err = e
                logger.warning(f"[dongsen] {ENGINE_LABELS[eng]} 合成失败: {e}")
            try:
                out.unlink(missing_ok=True)
            except OSError:
                pass

        logger.error(f"[dongsen] 两套都没合成出来: {last_err}")
        return None

    def _should_convert(self, text: str) -> bool:
        """判断一段文本适不适合转语音。

        注意：这里只做「粗筛」，真正能不能合成由 text_to_units 决定。
        早期版本这里放行英文、但转换器丢掉了英文字母，
        导致合成出空音频——现在转换器已支持字母，两边一致了。
        """
        t = (text or "").strip()
        if not t:
            return False
        try:
            lo = int(self._cfg("min_chars"))
            hi = int(self._cfg("max_chars"))
        except (TypeError, ValueError):
            lo, hi = 2, 150
        if len(t) < lo or len(t) > hi:
            return False
        # 至少要有一个可发音字符（汉字/字母/数字）
        if not any("\u4e00" <= c <= "\u9fff" or c.isalnum() for c in t):
            return False
        return True

    @staticmethod
    def _is_model_output(result) -> bool:
        """判断结果是否来自 LLM（含流式），而不是指令的普通回复。

        流式模式下本钩子会反复触发（每段一次），
        若每段都转语音会变成一条接一条的碎片，因此：
          LLM_RESULT        转换
          STREAMING_FINISH  转换（流式结束，内容已完整）
          STREAMING_RESULT  跳过（中间片段）
        """
        try:
            ctype = getattr(result, "result_content_type", None)
            if ctype is None:
                return False
            name = getattr(ctype, "name", "")
            return name in ("LLM_RESULT", "STREAMING_FINISH")
        except Exception:
            return False

    # ---------- 自动语音 ----------

    @filter.on_decorating_result()
    async def auto_voice(self, event: AstrMessageEvent):
        """发送前把 Bot 的回复替换成语音。"""
        if not self._auto_on():
            return
        if not self._any_engine():
            return

        result = event.get_result()
        if result is None:
            return

        if not self._is_model_output(result):
            return

        chain = result.chain
        if not chain:
            return

        # 收集所有 Plain 文本；图片等其他组件原样保留
        text_parts = []
        for comp in chain:
            if isinstance(comp, Comp.Plain):
                text_parts.append(comp.text)

        text = "".join(text_parts).strip()
        if not self._should_convert(text):
            return

        # 概率控制
        prob = self._prob()
        if prob < 100 and random.randint(1, 100) > prob:
            return

        session = event.unified_msg_origin
        self._cleanup()
        path = await self._synthesize(text, session)
        if not path:
            return

        try:
            record = Comp.Record.fromFileSystem(str(path))
        except Exception as e:
            logger.error(f"[dongsen] 构造语音消息失败: {e}")
            return

        others = [c for c in chain if not isinstance(c, Comp.Plain)]
        if self._cfg("send_text_too"):
            # 语音 + 原文字，方便阅读
            result.chain = [record, Comp.Plain(text)] + others
        else:
            result.chain = [record] + others

    # ---------- 指令 ----------

    @filter.command("动森")
    async def dongsen(self, event: AstrMessageEvent, text: str = ""):
        """用动森腔调说一句话：/动森 你好呀"""
        text = (text or "").strip()
        if not text:
            yield event.plain_result(
                "用法：/动森 要说的话\n"
                "比如 /动森 今天钓到大鱼了吗\n"
                "其他指令：/动森状态 /动森音高 /动森语速"
            )
            return

        if len(text) > TEXT_HARD_MAX:
            yield event.plain_result(f"太长了，最多 {TEXT_HARD_MAX} 个字。")
            return

        session = event.unified_msg_origin
        if not self._any_engine():
            yield event.plain_result(
                "两套引擎都关了，没得合成。去管理面板把「动森引擎」或"
                "「哔哔啵啵引擎」至少打开一个。"
            )
            return
        self._cleanup()

        path = await self._synthesize(text, session)
        if not path:
            yield event.plain_result("合成失败了，检查一下 ffmpeg 或音库文件？")
            return

        try:
            yield event.chain_result([Comp.Record.fromFileSystem(str(path))])
        except Exception as e:
            logger.error(f"[dongsen] 发送语音失败: {e}")
            yield event.plain_result("语音发送失败，看下日志。")

    @filter.command("动森音高")
    async def set_pitch(self, event: AstrMessageEvent, value: str = ""):
        """调整本群音高：/动森音高 440"""
        session = event.unified_msg_origin
        if not self._cfg("per_session_settings"):
            yield event.plain_result("管理员已关闭会话内调整，请到管理面板修改。")
            return

        if not value:
            yield event.plain_result(
                f"当前音高 {self._pitch(session):.0f} Hz\n"
                f"范围 {PITCH_MIN:.0f}-{PITCH_MAX:.0f}\n"
                f"用 /动森音高 440 修改，/动森重置 恢复默认"
            )
            return
        try:
            v = float(value)
        except ValueError:
            yield event.plain_result("要给个数字，比如 /动森音高 440")
            return
        if not (PITCH_MIN <= v <= PITCH_MAX):
            yield event.plain_result(f"音高要在 {PITCH_MIN:.0f}-{PITCH_MAX:.0f} 之间。")
            return
        self._session_pitch[session] = v
        yield event.plain_result(f"本群音高设为 {v:.0f} Hz。")

    @filter.command("动森语速")
    async def set_speed(self, event: AstrMessageEvent, value: str = ""):
        """调整本群语速：/动森语速 15"""
        session = event.unified_msg_origin
        if not self._cfg("per_session_settings"):
            yield event.plain_result("管理员已关闭会话内调整，请到管理面板修改。")
            return

        if not value:
            yield event.plain_result(
                f"当前语速 {self._ups(session):.0f} 音节/秒\n"
                f"范围 {UPS_MIN:.0f}-{UPS_MAX:.0f}\n"
                f"用 /动森语速 15 修改，/动森重置 恢复默认"
            )
            return
        try:
            v = float(value)
        except ValueError:
            yield event.plain_result("要给个数字，比如 /动森语速 15")
            return
        if not (UPS_MIN <= v <= UPS_MAX):
            yield event.plain_result(f"语速要在 {UPS_MIN:.0f}-{UPS_MAX:.0f} 之间。")
            return
        self._session_ups[session] = v
        yield event.plain_result(f"本群语速设为 {v:.0f} 音节/秒。")

    @filter.command("动森声线")
    async def set_voice(self, event: AstrMessageEvent, value: str = ""):
        """看或切本群声线：/动森声线 fish"""
        session = event.unified_msg_origin
        if not self._cfg("per_session_settings"):
            yield event.plain_result("管理员已关闭会话内调整，请到管理面板修改。")
            return

        if not value:
            eng, voc = self._pick(session)
            lines = [f"当前声线：{self._session_voice.get(session, self._voice(session))}",
                     f"这一句会用：{ENGINE_LABELS[eng]}（{voc}）" if eng else "这一句会用：无（两套都关）",
                     f"开着的引擎：{self._engines_text()}", "可选："]
            lines.append("  dongsen  动森腔（407 个真人音节拼的）")
            lines.append("  fish     哔哔啵啵·大肥鱼（尖，字头带小滑音）")
            lines.append("  lumo     哔哔啵啵·路墨（低，句尾往下落）")
            lines.append("  mix      开着的引擎里随机挑")
            lines.append("用 /动森声线 fish 切换，/动森重置 恢复默认")
            yield event.plain_result("\n".join(lines))
            return

        v = value.strip().lower()
        if v not in VOICES:
            yield event.plain_result(f"只认这几种：{'、'.join(VOICES)}")
            return
        self._session_voice[session] = v

        eng, voc = self._pick(session)
        if not eng:
            yield event.plain_result("记下了，但两套引擎都关着，现在不会出声。")
        elif VOICE_ENGINE.get(v, "") not in ("", *self._engines_on()):
            yield event.plain_result(
                f"{VOICE_LABELS[v]}属于{ENGINE_LABELS[VOICE_ENGINE[v]]}引擎，"
                f"那套现在是关的，所以实际会用{ENGINE_LABELS[eng]}（{voc}）。"
            )
        else:
            yield event.plain_result(f"本群声线设为 {v}，这一句会用{ENGINE_LABELS[eng]}（{voc}）。")

    @filter.command("动森诊断")
    async def diagnose(self, event: AstrMessageEvent):
        """检查运行环境，排查「没反应」类问题。"""
        ok = self._diag.get("ok", [])
        problems = self._diag.get("problems", [])

        lines = ["【动森语音 诊断】", ""]
        if problems:
            lines.append("❌ 发现问题：")
            for p in problems:
                lines.append(f"  · {p}")
            lines.append("")
        if ok:
            lines.append("✅ 正常项：")
            for o in ok:
                lines.append(f"  · {o}")
            lines.append("")

        # 当前配置
        s = event.unified_msg_origin
        eng, voc = self._pick(s)
        lines.append(
            f"配置：自动={'开' if self._auto_on() else '关'} "
            f"概率={self._prob()}% "
            f"引擎={self._engines_text()} "
            f"声线={self._session_voice.get(s, self._voice(s))} "
            f"音高={self._pitch(s):.0f} "
            f"语速={self._ups(s):.0f}"
        )
        lines.append(f"这一句会用：{ENGINE_LABELS[eng]}（{voc}）" if eng else "这一句会用：无（两套都关）")

        if problems:
            lines.append("")
            lines.append("建议：检查 AstrBot 版本是否 >= 4.0，"
                         "以及 dongsen/data/ 下的音库文件是否完整。")

        yield event.plain_result("\n".join(lines))

    @filter.command("动森重置")
    async def reset_session(self, event: AstrMessageEvent):
        """清除本群的临时设置，恢复管理面板配置。"""
        session = event.unified_msg_origin
        self._session_pitch.pop(session, None)
        self._session_ups.pop(session, None)
        self._session_voice.pop(session, None)
        yield event.plain_result(
            f"已恢复默认：声线 {self._voice(session)}，"
            f"音高 {self._pitch(session):.0f} Hz，"
            f"语速 {self._ups(session):.0f} 音节/秒"
        )

    @filter.command("动森状态")
    async def show_status(self, event: AstrMessageEvent):
        """查看当前所有设置。"""
        s = event.unified_msg_origin
        auto = "开" if self._auto_on() else "关"
        override = []
        if s in self._session_pitch:
            override.append(f"音高 {self._session_pitch[s]:.0f}")
        if s in self._session_ups:
            override.append(f"语速 {self._session_ups[s]:.0f}")
        if s in self._session_voice:
            override.append(f"声线 {self._session_voice[s]}")
        override_text = f"\n本群覆盖：{'、'.join(override)}" if override else ""

        yield event.plain_result(
            f"【动森语音设置】\n"
            f"自动语音：{auto}（概率 {self._prob()}%）\n"
            f"引擎：{self._engines_text()}\n"
            f"声线：{self._session_voice.get(s, self._voice(s))}\n"
            f"音高：{self._pitch(s):.0f} Hz\n"
            f"语速：{self._ups(s):.0f} 音节/秒\n"
            f"字数范围：{self._cfg('min_chars')}-{self._cfg('max_chars')}"
            f"{override_text}"
        )

    async def terminate(self):
        """插件卸载时清理临时文件。"""
        try:
            for f in self._tmpdir.glob("*.wav"):
                try:
                    f.unlink()
                except OSError:
                    pass
        except OSError:
            pass
