# 第三方资源与许可说明

本插件的语音库与合成算法来自以下项目：

## Coopanion

- **仓库**：https://github.com/Pal-AI-Lab/Coopanion
- **许可**：AGPL-3.0
- **使用的部分**：
  - `packages/cortico-world-desktop-pet/web/speech/zh.ogg` —— 语音库音频（407 个普通话音节）
  - `packages/cortico-world-desktop-pet/web/speech/zh.json` —— 音库清单（单元位置）
  - `packages/cortico-world-desktop-pet/src/speech/data/zh.json` —— 汉字读音表
  - `scripts/speech-bank/build.py` 的设计思路（音节切分、PSOLA 统一音高、EQ 参数）
  - `web/speech.js` 的播放逻辑（速率变调、声调曲线、节奏控制）

本插件对上述内容的改动：
- 用 Python + numpy 重新实现播放与重采样逻辑
- 音库从 ogg 额外转出 22.05kHz 的 WAV 版本，以支持无 ffmpeg 环境
- 增加了英文/数字的兜底发音（原项目用 CMU 词典，本插件用字母名近似）

## 许可影响

由于使用了 AGPL-3.0 授权的音库与算法，本插件整体按 **AGPL-3.0** 发布。

这意味着：
- 你可以自由使用、修改、分发本插件
- 如果你修改后通过网络提供服务，需要公开修改后的源码
- 分发时必须保留本文件与 LICENSE

原始音库的版权归 Coopanion 项目作者所有。
