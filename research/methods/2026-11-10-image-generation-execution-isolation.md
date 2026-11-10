# 莫奈 Skill 生图任务失配：开源源码研究与修复路线

**2026-11-10 · Status: RESEARCH_COMPLETE / REMEDIATION_NOT_IMPLEMENTED**  
**本轮无新增图片、无真实 A/B 分数、无额外付费服务调用。** 当前 `baseline` 与 `regional-p0` 保持不变。

## 1. 实际问题是什么

在 [P0 两次失败记录](../../benchmarks/original-paintings-v1/rounds/P0-2026-11-10-second-blocker.md) 中，请求单幅港口油画，却返回附带虚构分数的多栏评测报告。仓库的 `monet.py prepare` 只负责生成 `job.json`、`prompt.txt`、风格锁和检查表，**并不直接运行生图模型**。当前宿主执行途径未能证明准确传入了固定提示词、参考图像素、模型、画幅和角色关系。

已知故障是 `HOST_OUTPUT_ROUTING`；完整聊天中的评测资料可能影响了图像工具的意图识别，但**没有服务端原始 payload / 日志，不能把“上下文污染”认定为唯一原因**。这也不是已经证实的版权拒绝、P0 画法无效或莫奈风格问题。

## 2. 四个开源项目的真实做法

### A. OpenAI ImageGen Skill：显式提示词文件 + 明确 API 输出

- 固定源码：[OpenAI Skills](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431) / [image_gen.py](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.system/imagegen/scripts/image_gen.py) / [CLI 参考](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.system/imagegen/references/cli.md)。
- `_read_prompt` 只能选择 `--prompt` 或 `--prompt-file`，不能同时指定；没有提示词就报错。
- `--dry-run` 可以先检查请求 payload 与输出路径；真实生成显式调用 `client.images.generate(**payload)`，取 `result.data[].b64_json` 解码为图片文件。默认不悄悄覆盖现有文件。
- 这是一条**独立于默认内置生图工具的显式 CLI/API 路线**。官方 Skill 明确规定，只有用户主动选择 CLI fallback 才能使用；可能要求 API Key、配额和付费。不能自动替用户切换。

**对应修复：**让 `prompt.txt` 的原始字节经过独立的后端适配器，避免整段对话、评测说明或失败报告进入图像生成 payload；保存 `prompt_sha256`、模型与返回图片哈希。若无法证明传参，后端资格不通过。

### B. ComfyUI：结构化执行图、节点校验和任务回执

- 固定源码：[ComfyUI](https://github.com/comfyorg/comfyui/tree/605bfa18d262dbf5c3906b7bd11e7879113f1166) / [basic_api_example.py](https://github.com/comfyorg/comfyui/blob/605bfa18d262dbf5c3906b7bd11e7879113f1166/script_examples/basic_api_example.py) / [websockets_api_example.py](https://github.com/comfyorg/comfyui/blob/605bfa18d262dbf5c3906b7bd11e7879113f1166/script_examples/websockets_api_example.py) / [server.py](https://github.com/comfyorg/comfyui/blob/605bfa18d262dbf5c3906b7bd11e7879113f1166/server.py)。
- 示例在 JSON 节点中明确指定 `CLIPTextEncode.inputs.text`、`KSampler.inputs.seed`、宽高、模型 checkpoint；`POST /prompt` 不是要求宿主凭聊天推断参数。
- 服务端调用 `execution.validate_prompt`。非法图返回 400 与节点错误；正确时返回 `prompt_id`。客户端再通过 `/history/{prompt_id}` 以及 `/view` 读取对应真实输出。
- 有 `POST /upload/image`，可结合实际图像节点显式绑定参考图片。但**节点存在不等于图像模型必然理解“仅学画风，不复制题材”**，这是另外的质量验证问题。
- 成本是本地/云端服务、模型权重、GPU 显存、运维及许可证管理；不应一开始强制所有人安装。

**对应修复：**让每个请求具备 `task_id`、明确输入/模型/种子/画幅与绑定的图像资产，任务执行后按同一 ID 取回实际图片及输出记录。

### C. Hugging Face Diffusers：显式参数、随机数控制与可重复实验

- 固定源码：[Diffusers](https://github.com/huggingface/diffusers/tree/74fb49b5506a6960d55de0f7e6f4e0631213dc63) / [Reproducibility](https://github.com/huggingface/diffusers/blob/74fb49b5506a6960d55de0f7e6f4e0631213dc63/docs/source/en/using-diffusers/reusing_seeds.md) / [Conditional generation](https://github.com/huggingface/diffusers/blob/74fb49b5506a6960d55de0f7e6f4e0631213dc63/docs/source/en/using-diffusers/conditional_image_generation.md)。
- Pipeline 接收 `prompt`、`negative_prompt`、`generator` 等明确参数，`torch.Generator(...).manual_seed(...)` 约束随机性。
- 文档也指出底层算子、硬件、模型版本仍会引入差异，**固定 seed 不保证跨设备和版本逐像素复现**。

**对应修复：**A/B 冻结可取得的模型修订、调度器、生成尺寸、随机状态、参考图和时间窗口；无法拿到的值要写 `UNDISCLOSED`，不能猜测。

### D. Promptfoo：固定测试题与断言，但“有图像链接”不等于画对

- 固定源码：[Promptfoo](https://github.com/promptfoo/promptfoo/tree/b3603fab85bb331da98a8b68ca442e1f4af7e368) / [图像生成评测样例](https://github.com/promptfoo/promptfoo/blob/b3603fab85bb331da98a8b68ca442e1f4af7e368/examples/provider-replicate/image-generation/promptfooconfig.yaml)。
- 用独立的 `prompts`、`providers` 和 `tests.assert` 配置对照；可将同一题目交给不同后端。
- 但该示例仅检查返回字符串是否包含 Markdown 图像链接，不会验证它是不是单幅油画、有无双联拼版、有没有虚构分数。

**对应修复：**复用“测试题与生成输入分离”的组织方式，并单独设置画幅/图片文件校验和人工（或可审计视觉评审）硬门；未查看画面必须是 `NEEDS_REVIEW`，绝不可自动 PASS。

## 3. 对 Monet Skill 的最小改造方向（尚未执行）

```text
Frozen generation job (原始任务 + 风格规则 + SHA)
  ↓
Preflight: prompt/reference/role/model/size/权限 全部有证据
  ↓
显式后端执行：独立生成请求，不读评测报告正文
  ↓
真实 generation receipt + output image + SHA
  ↓
硬门：文件可解码 / 画幅 / 单幅画 / 内容 / 不含报告表格
  ↓
独立 style-review：原作仅评审用，笔触/色彩/空气感/纹理打分
  ↓
依据预注册 P0 标准决定保留基线还是继续测试
```

数据应分为 `generation_request.json`、`generation_receipt.json`、`style_review.json`，分别保存，并将它们与同一 `task_id` 绑定。生成器不读取研究报告、原作评分、旧版本分数；评审器只在确有图像输出时运行，不能用模型自述替代真实图片。

### 最小执行顺序

1. 保留 [`host_qualification.py`](../../benchmarks/original-paintings-v1/host_qualification.py) 作为事前门槛；无显式 prompt、真实参考像素/角色、模型标识、画幅与回执即 `BLOCKED_HOST_CAPABILITY`。
2. 先用**独立执行上下文**完成一张 MOR-01 港口的冒烟测试；对图像内容和画幅都做硬门，不让图表冒充画作。
3. 成功后，才恢复 3 个题材 × baseline/regional-p0 两臂的 6 张图。原作扫描仅用于评审，固定同一独立风格锚点；如后端无法隔离参考角色，明确降级结果，不冒充受控实验。
4. **不自动启用额外付费 API**，也不因研究而部署重型 GPU 服务或下载模型。需另行获得用户授权后才能试新的付费路径。

## 4. 证据与边界

这是基于开源真实源码的设计研究，没有运行这些项目的完整 GPU/图像推理、没有新图和画风评分。四个项目**没有承诺模型永远不会错画**；它们能做到的是把不透明的模型调用尽可能变成**有明确输入、明确执行路径、明确输出与失败证据**的流程。故障的唯一根因仍未证实。
