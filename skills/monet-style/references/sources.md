# 来源与实现取舍

本包原创实现。只借鉴参考角色分离、稳定配方、候选/验收分离等方法，没有复制未明确许可的 InstantStyle/CSGO 代码。项目里已有研究：

- https://github.com/QiuXu-Tech/monet-style-skill/tree/b65f3e6577d1ea5691d34de962670c7f4bbc74a4/research/methods/2026-11-09-style-content-control
- https://github.com/threerocks/hand-drawn-styles/tree/5a2f91fcbd32694a6caa9c7d09b2b3bad2666bc3
- https://github.com/yanliudesign/mono-color-skill/tree/c8ff70597ddedcd65f21a0b528f6a70c35690b0a

安装和宿主格式参考（核查 2026-11-09）：
- https://agentskills.io/specification
- https://developers.openai.com/codex/skills
- https://code.claude.com/docs/en/skills
- https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/imagegen/SKILL.md

图像事实、下载源和许可标记见 anchors.json。下载地址固定到本项目研究提交，字节通过 SHA-256 核验。开放图像的来源标记不等于博物馆为本项目背书。模型本身可能有独立使用条款。
