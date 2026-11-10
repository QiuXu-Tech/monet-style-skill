# P0 区域笔触实验 · ChatGPT ImageGen 真实探索记录与原作复现风险

**实验日期：2026-11-10**  
**状态：PARTIAL_EXPLORATORY / CONTROLLED_AB_NOT_QUALIFIED / NO_PROMOTION**  
**核对仓库基线：`main@e194dfcb927aed96b1282982f74596a1830b3a6e`，Skill 声明版本 `v0.4.0-alpha.4`。**

本记录对应 [P0 原计划](P0-regional-brushwork-plan.json)，单独保存已发生的失败和真实图像证据，不更改原计划 `NOT_RUN` 的**严格 A/B**状态。四张图由 ChatGPT 内置图像生成工具返回；未使用 ComfyUI、额外收费 API 或其他生成模型。

## 1. 实验输入的仓库真值

- 固定画法：`skills/monet-style/references/style-contract.json` 的 `prompt`。
- `regional-p0` 唯一候选规则：`skills/monet-style/references/regional-brushwork-p0.txt`；`scripts/monet.py:prepare` 仅对候选臂追加该文本。
- 三项题目、原文内容与目标画幅：`benchmarks/original-paintings-v1/cases.json`（MOR-01 4:3、MOR-02 4:5、MOR-03 3:2）。
- 原作对照协议：`benchmarks/original-paintings-v1/README.zh.md`。四维权重：笔触 30%、色彩 30%、氛围 30%、机械鳞纹控制 10%。
- 核对用原作：`research/reference-set/images/commons-132134.jpg`（《印象·日出》，1872），只作**生成后**比较，非生成内容图。此轮通过 GitHub 读取并查看了仓库中的原作复制图，但没有完成参考图字节级 SHA-256 的本机复核。
- 现有 Skill 的默认风格锚点是 `antibes-1888`，此轮**未证实**像素及其 style-only 角色实际送达后端。
- 三项原作跨越 1870s/1890s，不能视为当前 1880s 默认预设的同年代验证；分类为 `PUBLIC_DEVELOPMENT_OUT_OF_PROFILE_EXPLORATORY`。

## 2. 全部四次真实调用（无 best-of 挑选）

| # | 请求场景/意图臂 | 返回 gen_id | 原始 PNG SHA-256 | 实际画幅 | 硬门/状态 |
|---|---|---|---|---|---|
| 1 | MOR-01 港口 / baseline 意图 | `884c9457-a6fe-4870-a692-91f1de0b3bad` | `7d26526c6b7722df043b19a8c813bbef760658f5036c2737daf6af86052265fb` | 1536×1024 | 单幅、港口、雾中日出 OK；目标 4:3 **未达到** |
| 2 | MOR-01 港口 / regional-p0 意图 | `03de00ad-570f-4518-8749-428da1780c52` | `e7f0b990c9e613797ba680cbd3986ce7b1a956bf2523689775c3348056df4ee8` | 1536×1024 | 单幅、港口、雾中日出 OK；目标 4:3 **未达到** |
| 3 | MOR-02 阳伞女子 / baseline 意图 | `212fa5e8-696a-4186-9f28-c509ff2923fe` | `ea9b90ac41e6fe23aa47f82fa25efd34ea5e25bfe136845ab79201b7b858571f` | 1536×1024 | **REJECTED**：生成为港口，不是阳伞女子 |
| 4 | MOR-02 阶段的额外请求 / 臂未确认 | `75a2bd50-a743-4ec3-8aba-44b261383216` | `5d09fcb17c419c4fa1a4a5b02b0cd6a8c5a52f45ee0eb3eb1004e106128418bc` | 1536×1024 | **REJECTED**：仍生成港口，不是阳伞女子 |

实际返回的四幅均为独立绘画，不是先前失败的报告式拼图或信息图。图像原件保留在当前会话工作区/用户下载证据包，**未将生成 PNG 加入本公共仓库**。仓库记录的 SHA-256、gen_id 可用于日后由持图者核验；该记录本身不使源图可以从 GitHub 下载。MOR-03 干草堆的两个臂 **NOT_RUN**。由于 MOR-02 连续题材切换失败而停止追加生成。

## 3. 生成后视觉评分（非盲，不能归因于 P0）

评审者：GPT-6 模型视觉评审；检查生成图与馆藏原作在线/仓库复制图。各维 0–10，允许半分。**分数描述图像外观，不代表严格 A/B 的 P0 因果效应。**

| 已生成图像 | 笔触 30% | 色彩 30% | 氛围 30% | 鳞纹控制 10% | 描述性加权分 |
|---|---:|---:|---:|---:|---:|
| #1 港口，baseline 意图 | 5.5 | 6.0 | 6.0 | 6.0 | **5.85** |
| #2 港口，regional-p0 意图 | 5.0 | 6.0 | 5.5 | 5.5 | **5.50** |
| #3 和 #4（内容门失败） | null | null | null | null | **null** |
| MOR-03（未运行） | null | null | null | null | **null** |

- **图 #1，笔触：** 天空的较宽斜向笔与水面的短横向断笔有所区分，但天空质感偏厚重；**色彩：** 蓝灰与橙红的冷暖关系成立，桃橙色天空偏广；**氛围：** 港口雾中消融、前船可辨，表面笔痕削弱轻透感；**鳞纹：** 未见规整方格，但水面小碎笔仍重复。
- **图 #2，笔触：** 天空仍为浓密斜笔、水面大量类似短断笔，区域笔触优势不明确；**色彩：** 蓝灰/橙红关系存在，但暖色较强；**氛围：** 远景较软、前景可辨，天空纹理削弱空气连续性；**鳞纹：** 水面重复小色块显眼，不能确认控制得到改善。

**两幅的分数差不是 P0 改善/退步的证据。** 工具未提供可核实的精确 prompt 字节绑定、已验证的原作风格锚点和角色、明确的模型版本、随机种子及目标画幅。回执中 `prompt=""`、`seed=null`；`gen_id` 真实可得，后台模型的精确版本未披露。本轮符合港口题材的作品是 **2 张**，可用于严格受控 A/B 的配对是 **0 组**。

## 4. 新增风险检查：疑似签名及具体构图复现（用户指出）

用户观察：第 1 和第 4 张画面的左下角可能有莫奈签名，而且整体效果与原画很接近。

**独立核查：**
1. Musée Marmottan Monet 官方馆藏记录明确写有《印象·日出》**左下角署名 Claude Monet**，并有后补的“72”。馆藏页：<https://www.marmottan.fr/notice/4014/>；Wikimedia 复制图说明：<https://commons.wikimedia.org/wiki/File:Monet_-_Impression,_Sunrise.jpg>。
2. 实际放大检查生成图 #1 的左下角：有几段似连写字母的深色笔触；**无法可靠辨认成“Claude Monet”或“72”**。分类为 `POSSIBLE_SIGNATURE_LIKE_MARK`，不能假装已证实复制签名。
3. 生成图 #4 左下主要为凌乱的横向/斜向水色油画笔触，未见清晰可读的作者签名。分类为 `SIGNATURE_NOT_CONFIRMED`。
4. 整体看，两张均保留了原作熟悉的“雾港 / 工业剪影 / 橙日 / 垂直反光 / 前景小船”构图母题；具体船只位置、天际线及笔触结构与原作仍有差异。**风险是显著的原作内容/构图模仿，尚无逐像素复制证据。** 尽管原作像素未作为输入，生成工具可利用对著名作品的已有知识，无法证明没有内容记忆影响。

这种复现风险会污染“绘画语言可迁移性”的实验判断。后续需严格区分 **`style transfer`**（材质敏感笔触、光色组织、空气感）和 **`composition memorization / famous-work mimicry`**；对可疑署名设定单独审查与拒收门槛，不将图像很像原画当成画法能力。

## 5. 结论 / 后续

**INCONCLUSIVE / NO_PROMOTION。** 保持 `style-contract.json`、`regional-brushwork-p0.txt`、默认配置及评测权重不变；不发布性能提升声明。后续优先修复题材路由、模型身份、真实 prompt/anchor 绑定和画幅控制，并进行**构图解耦**的全套 3×2 测试及独立回归。旧图保留审计用途，不应作为未来严格 A/B 的新增样本。
