# 可选：显式 ComfyUI 本地生图执行器

> **工程试验状态**：这是可执行的本地后端适配器，不包含模型权重、GPU 服务或质量认证。默认只准备请求（dry-run）；真实调用需要明确追加 \`--execute\`。**没有 ComfyUI 服务时不会自动安装或启动它。**

## 为什么增加执行器

\`monet.py prepare\` 原本只生成 \`job.json\`、\`prompt.txt\` 和参考图描述。此前多次要求生成独立油画，宿主却返回附虚构评分的报告图，原因之一是**无法核实生成工作单是否准确送达模型**。新执行器遵循 [ComfyUI JSON 工作流和 prompt_id](https://github.com/comfyorg/comfyui/blob/605bfa18d262dbf5c3906b7bd11e7879113f1166/script_examples/websockets_api_example.py) 的可审计调用方式。

它**不读取聊天、评分模板、原作评估记录**，只读取明确指定的 \`job.json\`、用户已有的 API workflow JSON 与一个节点映射文件。

## 首版功能边界

- **仅支持**：单张文字生图 + 一张已核验的莫奈原作 style-only 参考图。支持现有 \`baseline\` 和 \`regional-p0\` 画法。
- **暂不支持**：\`restyle\`、cleanup 多参考、批量生成、ControlNet 自动配置、自动下载或部署模型、付费 API。
- 只连接显式的 \`http://127.0.0.1:<port>\` 或 \`http://localhost:<port>\`（以及 IPv6 loopback），不允许任意网络主机、URL 重定向和环境代理。
- 需要用户自己准备已测试的 ComfyUI **API Format** 工作流。必须有从 \`LoadImage\` 经实际风格条件节点到 \`KSampler\` 的上游路径；脚本验证依赖连接关系，**不声称仅凭连线可以证明模型学会了莫奈画法**。
- 适配器使用 ComfyUI 的 \`POST /upload/image\`、\`POST /prompt\`、\`GET /history/{prompt_id}\` 与 \`GET /view\`。输出必须是一张与请求宽高相同的 PNG；即使满足，仍标记 \`REQUIRES_VISUAL_REVIEW\`，绝不自动给风格评分。
- 由于无法在没有真实服务和具体模型的情况下确认后端可用性，本版测试使用了本机模拟 HTTP 服务。**11 项模拟/离线检查通过 ≠ GPU 推理成功**。

## 准备 ComfyUI

1. 自行安装并启动可信的 ComfyUI，确认本机 \`http://127.0.0.1:8188\` 可访问。
2. 在 ComfyUI 中创建**真实能运行且已经调通**的风格参考工作流，并以 **API Format** 导出 JSON。风格图节点必须是 \`LoadImage\`，其图像输出必须经已安装的风格控制/适配节点真正连接到 \`KSampler\` 的上游。不同模型和 IP-Adapter 组合的实现有差异，本包不捆绑或伪造节点。
3. 工作流包含且映射以下节点类型：\`CLIPTextEncode\`（正向）、\`EmptyLatentImage\`、\`KSampler\`、\`LoadImage\`（风格）、\`SaveImage\`、\`CheckpointLoaderSimple\`。缺失/不兼容时立即拒绝，不盲目运行。
4. 写一份仅映射节点 ID 的 \`mapping.json\`（下面 **示例 ID 必须按自己的导出文件修改**）：

\`\`\`json
{
  "positive": "6",
  "latent": "5",
  "sampler": "3",
  "style": "11",
  "save": "9",
  "checkpoint": "4"
}
\`\`\`

## 运行（先预检，再真实出图）

以下以 3:2 的现有 \`examples/train.json\` 为例：

\`\`\`bash
SKILL_ROOT=/path/to/monet-style
python3 "$SKILL_ROOT/scripts/monet.py" check
python3 "$SKILL_ROOT/scripts/monet.py" fetch --anchor antibes-1888

python3 "$SKILL_ROOT/scripts/monet.py" prepare \\
  --request "$SKILL_ROOT/examples/train.json" --out /tmp/monet-train-baseline \\
  --brushwork-variant baseline

python3 "$SKILL_ROOT/scripts/execute_comfyui.py" \\
  --job /tmp/monet-train-baseline/job.json \\
  --workflow /path/to/exported-api-workflow.json \\
  --mapping /path/to/mapping.json \\
  --width 1536 --height 1024 --seed 721 \\
  --out /tmp/monet-train-dry-run

# 只有明确准备实际执行时才加 --execute（创建新的输出目录）
python3 "$SKILL_ROOT/scripts/execute_comfyui.py" \\
  --job /tmp/monet-train-baseline/job.json \\
  --workflow /path/to/exported-api-workflow.json \\
  --mapping /path/to/mapping.json \\
  --width 1536 --height 1024 --seed 721 \\
  --out /tmp/monet-train-real-001 --execute
\`\`\`

输出：
- \`request.json\`：任务 ID、完整可审计的 ComfyUI 图和 SHA-256；
- \`receipt.json\`：明确说明 \`DRY_RUN_NO_MODEL_CALL\`、\`REQUIRES_VISUAL_REVIEW\`、\`REJECTED_TECHNICAL_OUTPUT\` 或失败与不确定结果；
- \`candidate.png\`：只有成功收到符合格式的图片时才出现。

对 P0 实验两臂，固定**相同的内容、风格参考、同一个 ComfyUI 工作流、同一个 checkpoint、同一种宽高和随机种子**，分别从 \`monet.py prepare\` 生成 baseline 和 regional-p0 的独立工作单。不要更改其他控制变量。原作《印象·日出》《撑阳伞的女人》和《干草堆》仅用于**视觉评审**，不作为目标内容参考图。

## 重要验收与安全原则

- 模型返回图片并不等于“画对了”。执行器只做文件/尺寸/任务关联检查。接下来必须单独检查**单幅画、主题、时段、重复鳞纹、色彩与空气感**，由真实评审填写证据后才进入评分。
- ComfyUI 插件是用户环境中的可执行软件，只应加载可信工作流与经审核的自定义节点。当前适配器不会自动修改 ComfyUI 配置或安装扩展。
- 实验中不承诺完全可重复。仅记录模型 checkpoint 的声明名称和 seed；若需要研究级复现，另需记录真实权重哈希、ComfyUI/插件版本和硬件。
- 请求图和响应图默认放在用户指定的本地新目录，不自动上传 GitHub；不要公开发布用户个人照片、私密提示词或 API/执行日志。
- 一旦提交返回未知结果，不自动重试同一请求。先核对 ComfyUI 的 \`/history/{prompt_id}\`。
- 当前宿主若缺少 ComfyUI 或必要风格节点，记录 \`NOT_SUPPORTED\`。不要静默退化为没有风格参考的纯文本图，却声称完成了受控 A/B。
