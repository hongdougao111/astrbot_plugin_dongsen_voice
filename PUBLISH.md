# 发布到 AstrBot 插件市场 · 操作清单

## 一、先改这一处（必须）

打开 `metadata.yaml`，把 `repo` 换成你的真实仓库地址：

```yaml
repo: https://github.com/YOUR_NAME/astrbot_plugin_dongsen_voice
```

`YOUR_NAME` 改成你的 GitHub 用户名。**这一项市场会校验，填错会导致发布失败。**

---

## 二、推到 GitHub

```bash
cd astrbot_plugin_dongsen_voice

# 建远程仓库（在 GitHub 网页上新建，名字用 astrbot_plugin_dongsen_voice）
git remote add origin https://github.com/YOUR_NAME/astrbot_plugin_dongsen_voice.git
git branch -M main
git push -u origin main
```

本地已经 `git init` 并完成首次提交，直接推即可。

---

## 三、提交到插件市场

1. 打开 https://cloud.astrbot.app/publish
2. 注册 / 登录 AstrBot Cloud 账号
3. 填入仓库地址：`https://github.com/YOUR_NAME/astrbot_plugin_dongsen_voice`
4. 提交审核

---

## 四、市场要求自查（已全部满足）

| 要求 | 状态 |
|---|---|
| 压缩包 ≤ 16MB | ✅ 2.72 MB |
| `metadata.yaml` 含必填项 | ✅ name/display_name/desc/version/author/repo |
| 无 `__pycache__` | ✅ 已排除（.gitignore） |
| 无 `.git` 目录 | ✅ 不会打包 |
| 有 LICENSE | ✅ AGPL-3.0（676 行全文） |
| 第三方资源说明 | ✅ THIRD_PARTY.md |
| 插件名格式 | ✅ `astrbot_plugin_` 前缀，全小写，无空格 |
| 代码可运行 | ✅ 干净目录解压后 85 项测试全通过 |

---

## 五、审核可能问的问题（提前准备）

### Q: 为什么用 AGPL-3.0？

音库和算法来自 [Coopanion](https://github.com/Pal-AI-Lab/Coopanion)，它本身是 AGPL-3.0。
按协议，衍生作品必须同协议发布。已写在 `THIRD_PARTY.md`。

### Q: 2.7MB 的包会不会太大？

主要是音库（WAV 3MB + ogg 415KB）。这是语音插件的必需品，不是冗余资源。
如果审核方介意，可以只保留 ogg（415KB）并加回 ffmpeg 依赖，但会失去零依赖优势。

### Q: 有没有收集用户数据？

没有。纯本地合成，不联网，不写数据库，不读用户消息以外的任何内容。

### Q: 会不会刷屏？

有概率控制（默认 100%，但可调到 1%），有字数上下限，指令回复不转语音。

### Q: 功能有没有明显缺陷？

**有，且已在 README 和 metadata 里如实标注**：

1. **多音字读错**——字表只存最常见读音。「银行」读成 yín xíng、
   「音乐」读成 yīn lè、「重新」读成 zhòng xīn、「了解」读成 le jiě。
   这是没有分词和上下文读音表导致的。
2. **英文按字母念**——`hello` 读 h-e-l-l-o，不是单词读音。
   参考实现用 CMU 词典，本插件没带（体积原因）。
3. **Markdown 链接的 URL 会被念出来**——`[链接](http://a.com)` 会多念一串字母。
4. **不支持日文/韩文**。
5. **未在真实 AstrBot 环境验证**——钩子逻辑照源码写，用伪造模块做了 67 项测试，
   但没在运行中的实例跑过。

这些都在仓库 README 的「已知问题」章节详细列出，没有隐瞒。

---

## 六、已知问题的技术原因（审核追问时用）

### 多音字

字表 `zh_table.json` 的格式是 `{"<音节><声调>": "<该读音的所有汉字>"}`，
每个字只出现在一个键里。要支持多音字，需要：

- 引入分词（如 jieba），按词查读音
- 或者维护一份「词 → 读音」的例外表

前者会增加依赖体积，后者需要大量人工标注。当前版本选择了简单方案。

### 英文

参考实现的流程是：
```
英文词 → CMU 词典查 ARPA 音素 → 映射到 IPA → 匹配最接近的普通话音节
```

CMU 词典压缩后约 2MB。本插件为了控制体积（已 2.7MB），改用字母名映射：
```
每个字母 → 一个固定的普通话音节
```

### 未验证真实环境

本机没有 AstrBot 运行环境，无法端到端验证。已做的工作：

- 下载 AstrBot 源码，核对 `on_decorating_result` 钩子签名
- 核对 `ResultContentType` 枚举的全部五种值
- 核对 `Comp.Record.fromFileSystem` 的实现
- 核对 OneBot 适配器的 `convert_to_base64` 路径
- 用伪造的 `astrbot` 模块跑 67 项逻辑测试

缺的是「真实 QQ 消息发出去有没有声音」这一步。

---

## 七、发布后的维护

### 改版本号

三处要同步：

1. `metadata.yaml` → `version:`
2. `main.py` → `@register(..., "1.2.0")`
3. `README.md` → badge 里的版本号

### 更新流程

```bash
# 改完代码
python selftest.py && python test_plugin.py   # 先跑测试
git add -A
git commit -m "fix: 描述改了什么"
git tag v1.2.1
git push && git push --tags
```

市场会自动拉取新版本。

---

## 七、当前测试状态

```bash
python selftest.py      # 18/18
python test_plugin.py   # 67/67
```

**85 项全通过**，不需要安装 AstrBot。

已覆盖的 BUG 回归：
- 英文静默丢字（曾导致 `hello` 合成空音频）
- 性能瓶颈（150 字从 2.66s 优化到 0.037s）
- 临时文件名 hash 碰撞与多进程不一致
- 配置越界与脏数据
- 流式回复碎片化
- 空音频发送
