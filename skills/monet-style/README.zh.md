# Monet Style · 0.4.0-alpha.4

可安装的莫奈画风 Agent Skill 工程升级版。新增 **clean-remake 集成路线**：当已有图片的大体氛围正确、但出现细碎鳞纹、脏渐变、重复微纹理或反复编辑劣化时，可在保持莫奈画法和原任务约束的同时，为宿主自动准备**构图量化图**与**低频光色辅助图**，用来指导干净重绘。

**这是实际 Skill 包，但不是独立生图模型。需要会话里已有支持图片参考的生图工具。工程检查不代表画风已经通过盲评。**

## 安装

把整个 `monet-style` 文件夹放到下列其中一个位置，不要只复制 SKILL.md：

- Codex 用户级：`~/.agents/skills/monet-style/`
- Claude Code 用户级：`~/.claude/skills/monet-style/`
- 项目级分别为 `.agents/skills/monet-style/` 或 `.claude/skills/monet-style/`。

如未发现新 Skill，重启相应客户端。此包没有自动改变你的全局配置，也没有安装图像模型。

使用 cleanup 时请求中的 `aspect_ratio` 必须匹配输入原图，若比例不一致，系统会拒绝以避免裁切或横竖方向漂移。

若要使用 cleanup 路线，请先安装 Pillow：

```bash
python3 -m pip install -r requirements.txt
```

## 标准生图

Codex 中直接说：

> 使用 $monet-style，画一座雨后傍晚的现代滨江城市，有三栋高楼和一条沿江步道。保留现代建筑，不添加教堂或睡莲。16:9。

Claude Code 中使用 `/monet-style`，但必须已有可调用的图片生成工具。没有工具时只能提示能力不足，不能假装出图。

## Clean-remake 升级路线

当已有图片的大体感觉对了，但纹理脏、鳞纹重、光晕假、笔触机械时，可使用 `mode: restyle` + `cleanup`。脚本会在运行目录自动生成：

- `cleanup/composition-map.png`：量化构图图，只负责布局、主体数量、遮挡、透视和大色块。
- `cleanup/gaussian-support.png`：可选的低频光色辅助图，只负责大范围光照、空气感和色温连续性。

**原始脏图默认仍保留作分析和复核，但在 cleanup 路线中，不应再被当作主要风格输入。**

```bash
python3 scripts/monet.py check
python3 scripts/monet.py fetch --anchor antibes-1888
python3 scripts/monet.py prepare --request examples/night-cleanup.json --out /tmp/monet-night-clean
```

准备成功后，由宿主读取工作单、附上参考图并调用真实生图工具。上述命令**不会自行生成图片**。

## 参考图

默认 Antibes 1888，另提供 Pourville 1882。首次使用由宿主执行 fetch 下载指定锚点，约 0.5–1.1 MiB；只有两幅都获取时才下载两幅。缓存经过 SHA-256 校验，可离线复用。源码包不捆绑完整 163 图研究集，不依赖其本地目录。

## 连续系列

```bash
python3 scripts/monet.py prepare --request examples/train.json   --lock /tmp/monet-city-run/style-lock.json --out /tmp/monet-train-run
```

不自动切换锚点、画法、cleanup 路线或版本。该锁不保证不同模型、硬件和会话逐像素复现；工具能力、实际模型标识和调用记录仍需保留。

## 原图转绘

将 request.json 中 `mode` 设为 `restyle`，`content_image` 指向用户真实提供的 PNG/JPEG。相对路径按 request.json 所在目录解析。参考照片不复制到开源仓库，脚本也不会上传它；只有宿主在用户的生图授权范围内将其传给实际工具。

如果同时启用 `cleanup`，宿主应按 `job.json` 中的角色附上：

1. 莫奈原作 style-only 参考；
2. cleanup-structure map；
3. 可选 cleanup-lighting support；
4. 原始 content image（analysis-only，若宿主无法分离角色则应明确降级或停止）。

## P0 笔触组织对照候选（默认关闭）

本版保留 alpha.2 的清洁重绘工程修复，同时提供一个 **opt-in 的区域笔触优化候选**。其重点是天空、水面、植被、衣裙、建筑/草垛的笔触方向、尺度和密度，不修改基线光色和朦胧规则；真正质量尚待验证。

```bash
python3 scripts/monet.py prepare --request examples/modern-city.json --out /tmp/monet-base --brushwork-variant baseline
python3 scripts/monet.py prepare --request examples/modern-city.json --out /tmp/monet-p0 --brushwork-variant regional-p0
```

生成前须按常规 `fetch` 获取相同原作参考图，或仅作 `--text-only` 规则检查（不能据此证明画风效果）。详细协议见 [P0 实验说明](references/regional-brushwork-p0.md)。

## 显式本机执行器（新增，可选）

此前的纯宿主生图路径多次把油画请求误画成评分报告。现新增 [ComfyUI 本地显式执行说明](references/explicit-comfyui.md) 和 `scripts/execute_comfyui.py`：从准备好的 `job.json` 显式传递完整 Prompt、参考图文件、实际宽高和固定种子，按 `prompt_id` 取回图片与回执。只支持文字生图 + 一张 style-only 锚点，需用户已有可信的 ComfyUI API 工作流和风格参考控制节点。

执行器**默认只进行本地 dry-run**，真实运行必须显式带 `--execute`；不启动 GPU、不下载模型、不调用付费 API。即便返回符合尺寸的图片，也只标为 `REQUIRES_VISUAL_REVIEW`，需独立验收。该功能已通过模拟 HTTP 服务测试，**尚未在真实 ComfyUI 模型上运行，也未验证画风分数。**

## 验收

宿主先查看生成结果，然后填写 review-template.json 的副本。用 inspect 取得图片哈希，填写逐项证据后执行 review，详见 references/review.md。缺少图片、来源角色或审看证据时不能登记通过。只有文字提示时可显式使用 `--text-only`，其结果始终标为降级路线。

本版不提供 GPU 服务、ControlNet、LoRA、API Key 管理或自动收费重试；不假装封闭图像工具暴露内部注意力参数。源代码采用 MIT；原作参考保留单独的 CC0 来源说明。受 `clean-remake-image-skill` 启发的方法研究已另行记录，但这里整合的是我们自己的实现与工作流。

## R001 工程/出图路由状态

真实生图调用曾错误返回带虚构评分的报告图，已按 `single_painting_canvas` 审查门禁拒收。**没有完成过受控的真正多参考清洁重绘，更没有有效的画风提升分数**。这属于实验失败记录，不得当成 0.4.0 成功的视觉案例。
