# Monet Style Skill

**Status: 工程实验版 0.4.0-alpha.3（默认基线不变，P0 区域笔触为可选实验）。真实 A/B 画风增益仍未验证。**

本项目由 QiuXu-Tech 发起，以 Claude Monet 的原作为研究基础，探索跨题材、跨光照保持绘画语言一致性的开源图像生成 Agent Skill。

**Research before claims.** 不将“印象派滤镜”、睡莲图案、油画噪声视作莫奈风格；不把单元测试通过等同于视觉质量通过。早先 `monet-stable` 草稿没有并入正式实现。

## 可安装的 Skill

入口：[skills/monet-style/SKILL.md](skills/monet-style/SKILL.md) · [中文安装与用法](skills/monet-style/README.zh.md) · [工程测试记录](docs/implementation-validation.json)

将 `skills/monet-style/` 整个目录复制到 Codex 的 `~/.agents/skills/`，或 Claude Code 的 `~/.claude/skills/`。宿主必须已有支持真实图片参考的生图工具。安装 Skill 不会自动提供生图模型。

```bash
# 在仓库根目录验证与打包，普通规则检查无第三方依赖，cleanup 预处理需要 Pillow
python3 -m unittest discover -s tests -v
python3 skills/monet-style/scripts/monet.py check
python3 tools/package_skill.py --output dist/monet-style-0.4.0-alpha.3.zip
```

实际使用：`使用 $monet-style，画一列驶入现代车站的高速列车，保留现代车头，3:2。`

本版实现固定画法文本、两幅原作锚点按需下载与 SHA-256 校验、内容/风格角色分离、系列输入锁、宿主生图调用指令和逐图验收记录。默认 1880s 只是可修订的实验基线，非最终艺术风格定稿。没有 GPU 服务、模型权重、LoRA 或隐藏付费调用。

## 可复用优化循环

[优化计划 V1.0](docs/optimization/README.zh.md) · [单轮执行指令](docs/optimization/EXECUTE_ONE_ROUND.zh.md) · [已复核的工程基线](docs/optimization/rounds/R000-baseline.json)

每轮依据真实失败做最小修改，分阶段出图、评审与回归；计划不自动启动后台任务或付费生图，视觉基准仍待执行。

[P0 后端资格检查与第二次路由失败记录](benchmarks/original-paintings-v1/rounds/P0-2026-11-10-second-blocker.md) · [P0 区域笔触候选与操作说明](skills/monet-style/references/regional-brushwork-p0.md) · [待执行的对照计划](benchmarks/original-paintings-v1/rounds/P0-regional-brushwork-plan.json) · [Alpha.2 真实失败记录](docs/optimization/rounds/R001-results-2026-11-10.md)

**本轮 21 项离线测试通过，真实生图与画风改进仍未获验证。**

## 原作图像参考集

- [莫奈原作学习参考集（图片、来源与授权）](research/reference-set/README.md)

## Research documents

- [莫奈原作对照评测协议 V1：笔触、色彩与氛围](benchmarks/original-paintings-v1/README.zh.md)

- [Clean Remake Image Skill：纹理污染与清洁重绘方法研究](research/methods/2026-11-09-clean-remake-image-study.md)

- [指定画风稳定生成：源码研究、契约检查与实验方案](research/methods/2026-11-09-style-content-control/README.zh.md)
- [原作研究目录](research/artworks.md)
- [初步画风观察和待验证假设](research/style-study.md)
- [研究和测试路线](research/roadmap.md)

## Principles

1. 以权威馆藏原作为优先证据，保留逐件来源；分开标注事实、视觉解释和假设。
2. 比较 1870s、1880s、1890s 系列画及晚期水景；实验预设可修订，不把不同时期混成统一滤镜。
3. 画风可以迁移到新题材，不应复刻现有名作的具体内容与构图。
4. 图片引用需逐件检查使用授权；已收录的研究副本保留逐件来源与授权标记，不因项目 MIT 许可而改变图片权利。
5. 工程 alpha 可安装供测试；“稳定版”声明必须经过真实生图、跨题材对照和视觉评审。未运行的测试明确标为 NOT_RUN。

## License

原创研究笔记和自主代码采用 MIT。第三方原作图片、网页内容、商标不属于本仓库 MIT 授权范围；Skill 内见 [ASSET-LICENSE.md](skills/monet-style/ASSET-LICENSE.md)。用户原图和生图结果不自动提交到仓库。
