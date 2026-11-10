# P1 人物局部笔触 · ChatGPT ImageGen 拼版路由失败及独立单图提示词

**记录日期：2026-11-11（Asia/Singapore）**  
**状态：HOST_OUTPUT_ROUTING_FAILURE / ZERO_VALID_NEW_PAINTINGS / NO_STYLE_SCORES / NO_PROMOTION**  
**目的：** 在 MOR-02 草坡撑伞女子题材下，试验用户指出的“面部和手部过于精致、规整”的问题，同时保留此前色彩关系。

## 本次实际调用

- 使用 ChatGPT 内置 `image_gen.text2im` 发起一次生成。意图是在同一题材下产生独立单幅油画供后续评分；事前未授权输出比较报告、拼图、评分表或虚构评审。
- 返回生成 ID：`83df5dea-3410-4597-9a9e-1a2cd2a57b6e`。
- 实际文件为 **1122×1402 PNG**，2,544,703 字节，SHA-256 为 `f60f979fad5756b84b346aeac6cc316c2c1ccd22fc4eb026d8ea75e66ff19a76`。
- 返回的是**包含多格对照与未经真实生成/评审就写入分数的信息图**，不符合独立单幅绘画要求。它不是四张独立生成图片，不能把拼版中的局部画面拆开冒充不同生成回执。
- 工具回执 `prompt=""`、`seed=null`，未披露具体模型修订版本、正式输入提示词的绑定或 style anchor 角色绑定。
- 失败分类：`HOST_OUTPUT_ROUTING_FAILURE` / `single_painting=FAIL` / `REJECTED`。有效生成油画 = **0**，四维评分全部 `null`。尤其禁止引用图中自称的 **5.90、6.40、6.70、6.55** 等分数：并没有与这些版本一一对应的真实调用和独立评分。
- 失败后立即停止在本会话中的其他图像生成调用；没有启用 ComfyUI、其他生图模型或新增收费 API。该输出没有上传至公共仓库。

## 对照恢复方案：分开生成、分开评分

提供三份**只有单图生成指令**的独立文本工作单，均为 MOR-02 的同一中文场景、竖幅 4:5、相同 compact-v1 主画法。每份各自复制到**全新** ChatGPT 对话单独生图；任务说明、A/B/C 标签、旧图、评估数据以及其他场景均不能出现在图片提示文本中。

| 实验臂 | 独立提示词内容变化 | UTF-8 SHA-256 |
|---|---|---|
| A `compact-v1` | 与此前 MOR-02 compact 提示词完全一致 | `0e00ebe7fc3ac8ca67294ae843f6092450ba051229780f3f9928697a4241afa6` |
| B `compact-v1 + P1` | **仅在 A 后追加**面部/手部的色块概括与不规则笔触规则 | `81f7e6cf9bfe9a0fcc3cadaa0a2c68881f33e0b3c4e363c90de5c7d62f68eb6a` |
| C `compact-v1 + P1 + compact-regional-p0` | 在 B 后追加已存在的 compact 区域笔触文本 | `f13f73c52240b14d5c9b0ee75318b26283b3bf9e8378f17af78adc0dd705f0b7` |

`P1` 的唯一候选增量（尚未作为默认或正式 P0 overlay 写入代码）：

```text
Faces and hands: suggest features with grouped warm/cool paint planes and a few irregular, directional strokes; avoid polished facial linework or individually outlined fingers while keeping anatomy, pose and gesture readable.
```

`C` 的第二增量直接复用仓库 `skills/monet-style/references/compact-regional-p0.txt`。A vs B 可探讨 P1 的作用；B vs C 探讨 P0 额外效果。A vs C 同时变化两项，不能归因于单一因素。

在新的会话中也不能控制 ChatGPT 图像工具的内部模型修订版本、随机种子和真实风格图像绑定，因此**即使生成成功也只能称探索性对照**。先审核每张画的主体/天气/竖幅/单幅格式/署名风险，失败不评分；通过后分别由用户与模型独立按笔触 30%、色彩 30%、氛围 30%、鳞纹控制 10% 打分，再比较具体缺陷区域。

**截至本次记录，没有新增合格的 P1 生图样本、人工评分或性能提升证据。** 保留此前用户对原始 MOR-02 单幅样本的 **4/8/6/5（5.90）** 分和原有模型 7.35 分为不同评审来源，不把本次无效拼版的数字混入任何一方。

**决策：CONTINUE_EXPLORATORY / NO_PROMOTION。** 不修改 `full`、`compact-v1` 或默认画法，只保留实验提示词与故障记录。
