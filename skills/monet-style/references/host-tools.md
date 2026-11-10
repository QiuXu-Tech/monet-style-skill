# 宿主与工具适配

Skill 是宿主执行的工作流；本包不是独立生图模型，也不自带网络生图客户端。`scripts/monet.py` 负责输入、参考校验、cleanup 预处理和结果登记，不执行图像推理。

| 宿主能力 | 本版行为 |
|---|---|
| 生图工具支持真实图片参考 | 使用已查看、哈希一致的原作作 style-only 输入，并实际调用该工具 |
| 同时支持内容图与风格图 | 可运行 restyle；明确两个输入各自作用 |
| 支持多张参考图且角色可控 | 可启用 cleanup route，把结构图和低频光色图分别作为独立参考 |
| 只支持纯文字 | 正式参考模式为 NOT_SUPPORTED；仅在明确选择时输出 PROMPT_ONLY |
| 不能查看生成图片或不能访问返回文件 | 交付 unreviewed candidate；不填写通过记录 |
| 没有生图工具 | 明确缺少能力；安装 Skill 不会凭空赋予生图模型 |

## Codex

已有内置 image_gen 时优先使用它，不为此要求用户再创建 API Key。实际参数以当前工具 schema 为准。官方 imagegen Skill 也可作为宿主执行入口，但不得假设其路径、版本或参数固定。若工具由上下文推断指令，使用它真实支持的上下文输入；若工具要求真实资产引用，则必须先取得支持的引用。把本地路径写进 prompt 不等于图片已附上。

若启用 cleanup 路线，需要确认工具是否真的允许多张参考图各自发挥不同作用。若不能把“style anchor / structure map / gaussian support / content image”清晰区分，应停止或降级，而不是口头假设模型会自己理解。

## ChatGPT 内置图像工具：上下文推断隔离路线

部分会话中的内置生图工具只从对话历史推断图片任务，无法提供可核验的独立 `prompt` 字段、模型快照或种子。在本项目中，曾连续要求生成阳伞女子而返回旧港口场景。**这是实际内容路由失败，不足以证明具体后端内部根因。**

如果本次会话已有旧题材、生图、评分或实验报告，不要在本会话反复要求换题材，也不要把实验计划/先前结果写进图片提示。仓库仅提供可审计的隔离包，不能通过 CLI 控制 ChatGPT 会话或后台模型：

```bash
python3 benchmarks/original-paintings-v1/generation_preflight.py prepare \
  --case MOR-02 --variant baseline --prompt-variant compact-v1 \
  --delivery-profile chatgpt-inferred --conversation-state reused \
  --output /tmp/monet-mor02-clean
```

返回 `BLOCKED_CONTEXT_REUSE`：这不是调用失败，表示**不要在旧聊天中执行图片工具**。打开一段全新 ChatGPT 对话，仅粘贴 `image-only-prompt.txt` 的正文，直接请求一幅画；不要附上 GitHub 研究记录、历史生成图、评分、实验说明或第二个场景。只有在**实际**新会话中，才将 `--conversation-state` 改为 `fresh`；返回 `FRESH_CHAT_EXPLORATORY_ONLY`，仍非严格受控 A/B。此状态基于操作者声明，不是系统认证。每幅图必须先单独通过题材、天气、画幅和单幅画门禁，再做视觉评分。错误题材应保存回执、记 `CONTENT_GATE_REJECTED` 并停止该会话，不跨臂复用错误结果。

`image-only-prompt.txt` 只是完整提示词文本，**并不能把它自动送入 ChatGPT 生图工具**。本路线是人工隔离缓解办法，不能保证消除所有内容路由错误，也不能证明原作 style anchor 像素已被正确送达。需要严格 A/B 时按 [宿主资格门禁](../../../benchmarks/original-paintings-v1/host_qualification.py) 另行核查；不符合前置条件就不得宣称受控实验。

## Claude Code

按 Agent Skills 格式可安装本包，但是否能生图取决于该会话实际连接的工具。不能把“Claude Code 可读取 SKILL.md”解释为“Claude Code 原生具备本包需要的生图能力”。已有的图片 MCP/工具只在 schema 和权限允许时调用；本包不自动安装、连接或付费订阅任何服务。

## 工具规则优先

某些宿主要求生成后停止，不允许紧接着视觉验收；此时保留候选状态，不违规调用工具。支持审看时再完成 review。不得忽略系统安全规则、偷偷转用模型/API、伪造种子或模型快照。文件路径、私有照片、完整提示和任务记录默认留在用户本地；不得因为项目是开源而自动提交用户图片。

官方规范核查日期：2026-11-09。参见 [sources.md](sources.md)。
## 显式本机 ComfyUI（可选、独立于宿主默认生图路径）

见 [explicit-comfyui.md](explicit-comfyui.md)。用户需自行提供已经验证的 API workflow 与 style-image 条件节点；默认 dry-run，`--execute` 才提交本地 `/prompt`。仅从 `job.json` 获得绘画指令，不从聊天和评测文档推断提示词。此路径不改变此前的 Codex / Claude Code 内置工具调用行为；没有 ComfyUI 服务时应报告不可运行。
