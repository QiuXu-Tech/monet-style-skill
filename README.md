# Monet Style Skill

**Status: Research / 艺术研究阶段 — 尚未开发或验证生图 Skill。**

本项目由 QiuXu-Tech 发起，以 Claude Monet 的原作为研究基础，最终探索可以跨题材、跨光照保持绘画语言一致性的开源图像生成 Agent Skill。

**Research before prompts.** 不将“印象派滤镜”、睡莲图案、油画噪声视作莫奈风格；也不把此前的未经实测的初版 Skill 直接作为正式实现。

## Research documents

- [原作研究目录](research/artworks.md)
- [初步画风观察和待验证假设](research/style-study.md)
- [研究和测试路线](research/roadmap.md)

## Principles

1. 以权威馆藏原作为优先证据，保留逐件来源；分开标注事实、视觉解释和假设。
2. 比较 1870s、1880s、1890s 系列画及晚期水景的异同；**不预先锁定风格时期**。
3. 画风可以迁移到新题材，不应复刻现有名作的具体内容与构图。
4. 图片引用需逐件检查使用授权；目前仓库不收录第三方原作图片。
5. 只有完成模型出图和对照评测后才发布真实的 SKILL.md，并报告评测结果与局限。

## License

原创研究笔记和后续自编代码采用 MIT，第三方原作图片、网页内容、商标不属于本仓库 MIT 授权范围。