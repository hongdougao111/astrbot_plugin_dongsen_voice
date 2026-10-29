---
name: Bug 报告
about: 插件不工作、报错、或者行为不对
title: "[BUG] "
labels: bug
---

## 问题描述

<!-- 一句话说清楚发生了什么 -->

## 复现步骤

1.
2.
3.

## 期望行为

<!-- 你觉得应该怎样 -->

## 实际行为

<!-- 实际发生了什么 -->

## 环境信息

- AstrBot 版本：
- 插件版本：
- 平台适配器：<!-- aiocqhttp / qq_official -->
- 操作系统：
- Python 版本：

## 日志

<!-- 把 AstrBot 日志里含 [dongsen] 的部分贴上来 -->

```
（粘贴日志）
```

## 配置

<!-- WebUI → 插件 → 动森语音 → 配置，截图或粘贴关键项 -->

- 启用自动语音回复：
- 自动语音触发概率：
- 音高：
- 语速：
- 最大字数：

## 自查

- [ ] 已确认插件目录在 `AstrBot/data/plugins/` 下
- [ ] 已确认 `dongsen/data/zh.wav` 存在（约 3MB）
- [ ] 已重载过插件
- [ ] 日志里没有 `ModuleNotFoundError`
