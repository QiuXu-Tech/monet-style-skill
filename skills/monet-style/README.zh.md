# Monet Style · 0.3.0-alpha.1

可安装的莫奈画风 Agent Skill 工程初版。支持文字生图和已有照片转绘的宿主工作流，提供固定画法文本、两幅可核验原作参考、系列输入锁和逐图验收记录。

**这是实际 Skill 包，但不是独立生图模型。需要会话里已有支持图片参考的生图工具。工程测试不代表画风已经通过盲评。**

## 安装

把整个 `monet-style` 文件夹放到下列其中一个位置，不要只复制 SKILL.md：

- Codex 用户级：`~/.agents/skills/monet-style/`
- Claude Code 用户级：`~/.claude/skills/monet-style/`
- 项目级分别为 `.agents/skills/monet-style/` 或 `.claude/skills/monet-style/`。

如未发现新 Skill，重启相应客户端。此包没有自动改变你的全局配置，也没有安装图像模型。

Codex 中直接说：

> 使用 $monet-style，画一座雨后傍晚的现代滨江城市，有三栋高楼和一条沿江步道。保留现代建筑，不添加教堂或睡莲。16:9。

Claude Code 中使用 `/monet-style`，但必须已有可调用的图片生成工具。没有工具时只能提示能力不足，不能假装出图。

## 参考图

默认 Antibes 1888，另提供 Pourville 1882。首次使用由宿主执行 fetch 下载指定锚点，约 0.5–1.1 MiB；只有两幅都获取时才下载两幅。缓存经过 SHA-256 校验，可离线复用。源码包不捆绑完整 163 图研究集，不依赖其本地目录。

```bash
python3 scripts/monet.py check
python3 scripts/monet.py fetch --anchor antibes-1888
python3 scripts/monet.py prepare --request examples/modern-city.json --out /tmp/monet-city-run
```

准备成功后，由宿主读取工作单、附上参考图并调用真实生图工具。上述命令**不会自行生成图片**。

## 连续系列

```bash
python3 scripts/monet.py prepare --request examples/train.json \
  --lock /tmp/monet-city-run/style-lock.json --out /tmp/monet-train-run
```

不自动切换锚点、画法或版本。该锁不保证不同模型、硬件和会话逐像素复现；工具能力、实际模型标识和调用记录仍需保留。

## 原图转绘

将 request.json 中 `mode` 设为 `restyle`，`content_image` 指向用户真实提供的 PNG/JPEG。相对路径按 request.json 所在目录解析。参考照片不复制到开源仓库，脚本也不会上传它；只有宿主在用户的生图授权范围内将其传给实际工具。

## 验收

宿主先查看生成结果，然后填写 review-template.json 的副本。用 inspect 取得图片哈希，填写逐项证据后执行 review，详见 references/review.md。缺少图片、来源角色或审看证据时不能登记通过。只有文字提示时可显式使用 `--text-only`，其结果始终标为降级路线。

本版不提供 GPU 服务、ControlNet、LoRA、API Key 管理或自动收费重试；不假装封闭图像工具暴露内部注意力参数。源代码采用 MIT；原作参考保留单独的 CC0 来源说明。
