# Monet Style Skill

**Status: 0.5.0-alpha.2 · V3-W02笔触构形修订，保留1880s及Antibes1888锚点；真实视觉A/B待验证。**

本项目由 QiuXu-Tech 发起，以 Claude Monet 的原作为研究基础，探索跨题材、跨光照保持绘画语言一致性的开源图像生成 Agent Skill。

**Research before claims.** 不将“印象派滤镜”、睡莲图案、油画噪声视作莫奈风格；不把单元测试通过等同于视觉质量通过。早先 `monet-stable` 草稿没有并入正式实现。

## 2026-11-19 V3-W02｜让笔触构成形体

根据真实返回图及用户批评，修订默认核心规则，避免“漂亮数字风景+整齐油画纹理”。原V3核心原样保留为 `research-v3-previous`，水面模块不变。详见[修订与对照方案](docs/V3-W02-paint-construction-2026-11-19.zh.md)。此修改不是视觉效果已提升的证明。

## 2026-11-18 研究指导升级

[完整更新与验证记录](docs/research-upgrade-2026-11-18.zh.md) · [九篇原作研究索引](research/artwork-studies/README.zh.md) · [运行时证据与适用边界](skills/monet-style/references/artwork-evidence.md)

本次根据用户明确要求更新Skill：将形体与局部笔触分开处理，把结构、光照、距离和视觉作用带入区域选择；让光照影响颜色、边缘与可见细节；避免统一雾化、全面精修与全图厚涂。花园、水面、人物、建筑、雪景、海岸按需选用，保留有意的整体节奏，不把机械鳞纹控制等同于随机化或删除所有短笔触。

工作流先区分提示词、评审、研究和授权生成。本项目仍由用户另开对话生成测试图；提示词直接在聊天中完整给出。评审使用对应原作四维10分定义锚点，权重30/30/30/10；缺图、未审看或硬门未知时不计算有效总分。

新版默认 `research-v3`，旧核心保存在 `legacy-v2`，历史P0仅配合旧配置。Draft PR #1与历史研究/实验记录保持独立。这是可回溯的规则更新，尚无新版真实生成图或视觉提升分数。

## 可安装的 Skill

入口：[skills/monet-style/SKILL.md](skills/monet-style/SKILL.md) · [中文安装与用法](skills/monet-style/README.zh.md) · [工程测试记录](docs/implementation-validation.json)

将 `skills/monet-style/` 整个目录复制到 Codex 的 `~/.agents/skills/`，或 Claude Code 的 `~/.claude/skills/`。实际参考受控生图需要宿主支持真实图片参考；准备提示词和评审不要求调用生图工具。安装 Skill 不会自动提供生图模型。

```bash
# 在仓库根目录验证与打包，普通规则检查无第三方依赖，cleanup 预处理需要 Pillow
python3 -m unittest discover -s tests -p test_monet.py -v
python3 -m unittest discover -s skills/monet-style/tests -p 'test_*.py' -v
python3 skills/monet-style/scripts/monet.py check
python3 tools/package_skill.py --output dist/monet-style-0.5.0-alpha.2.zip
```

实际使用：`使用 $monet-style，画一列驶入现代车站的高速列车，保留现代车头，3:2。`

本版实现研究指导的核心画法与按需题材模块、两幅原作锚点按需下载与 SHA-256 校验、内容/风格角色分离、系列输入锁、提示词交付和逐图验收记录。默认 1880s 只是可修订的实验基线，非最终艺术风格定稿。没有 GPU 服务、模型权重、LoRA 或隐藏付费调用。

## 可选的显式 ComfyUI 执行器（实验功能）

[执行器说明](skills/monet-style/references/explicit-comfyui.md) · [源码](skills/monet-style/scripts/execute_comfyui.py) · [Mock 后端测试](skills/monet-style/tests/test_execute_comfyui.py)

保留的可选适配器可以在用户已运行且配置好风格控制工作流的**本地 ComfyUI** 上，明确传入提示词、原作参考、宽高和种子并按任务 ID 取图。默认 dry-run，不自动下载模型、调用收费 API 或重试未知结果。模拟服务端 12 项验证通过，尚未完成真实 GPU 模型生图和莫奈画风 A/B 评测。

**[Alpha.4 双设备测试报告](docs/alpha4-regression-2026-11-10.json)**：Mac 55 项通过、14 项因 Pillow 缺失跳过；Windows 69/69 项通过。真实 ComfyUI 推理仍未执行。

## 可复用优化循环

[优化计划 V1.0](docs/optimization/README.zh.md) · [单轮执行指令](docs/optimization/EXECUTE_ONE_ROUND.zh.md) · [已复核的工程基线](docs/optimization/rounds/R000-baseline.json)

每轮依据真实失败做最小修改，分阶段出图、评审与回归；计划不自动启动后台任务或付费生图，视觉基准仍待执行。

[P0 后端资格检查与第二次路由失败记录](benchmarks/original-paintings-v1/rounds/P0-2026-11-10-second-blocker.md) · [P0 区域笔触候选与操作说明](skills/monet-style/references/regional-brushwork-p0.md) · [待执行的对照计划](benchmarks/original-paintings-v1/rounds/P0-regional-brushwork-plan.json) · [Alpha.2 真实失败记录](docs/optimization/rounds/R001-results-2026-11-10.md)

**上述21项为早期P0离线测试记录，非本版测试总数；当前验证见本次升级记录。真实生图与画风改进仍未获验证。**

## 原作图像参考集

- [莫奈原作学习参考集（图片、来源与授权）](research/reference-set/README.md)

## Research documents

- [生图输出错误路由：OpenAI ImageGen / ComfyUI / Diffusers / Promptfoo 源码研究](research/methods/2026-11-10-image-generation-execution-isolation.md)

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
