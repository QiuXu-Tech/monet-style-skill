# Compact prompt V1 · ChatGPT ImageGen host-routing smoke test

**日期：2026-11-11（Asia/Singapore）；UTC：2026-11-10 17:04–17:07 左右**  
**状态：BLOCKED_HOST_OUTPUT_ROUTING / NO_VALID_PAIR / NO_PROMOTION**  
**候选工程版本：** PR #1, `be55c0a64ef2d5526320678b73e3da38308f99c4`（对比 `main@f030f77e0b4958f58c58a1e86a04ab30fa637e05`）。本记录不宣称候选提示词实际到达生成模型。

## 意图与实际行为

- 预期测试目标：MOR-02；初夏草坡上的撑阳伞女子；微风吹动浅色裙摆，明亮白云、草地；略低视角；**一张竖向 4:5 油画**。
- 计划方式：先做 `full` 画法的单图题材切换冒烟测试，若成功再尝试 `compact-v1`；实际没有执行第二臂。
- 图像工具：本会话的 ChatGPT 内置 `image_gen.text2im`，只调用 **1 次**。**模型 ID/修订版、seed、显式 prompt 参数绑定与风格锚点像素/角色均不可核实**。
- 真实生成回执：`gen_id = 2f3b3026-7d79-424c-bf5c-c01356bb05e6`；`parent_gen_id = null`；回执中的 `prompt = ""`，`seed = null`。
- 实际内容：**雾中日出港口、橙色太阳、水面反光、前景双人小船、船桅与烟囱**，与 MOR-02 题材完全不符；工具的自动生成描述也继续写成 harbor at sunrise，而不是女子草坡。
- 图像输出：PNG，实际 **1448×1086**（约 4:3，而非请求的竖向 4:5），SHA-256：`45f2909419f995e75bd9ba60f7b8422b68ae1d7052a891721f110aa03584bbff`，文件字节长度 **2,870,420**（本次本机读取结果）。
- 此 PNG 在当前 ChatGPT 会话附件中保存，**没有加入公开 GitHub 仓库**。

## 门禁与实验资格

| 门禁 | 结果 | 观察 |
|---|---|---|
| `single_painting` | PASS | 单幅独立油画，无拼图/分栏/评分表 |
| `subject_class` | FAIL | 实际为港口，不是撑阳伞的女子 |
| `time_and_weather` | FAIL | 实际为雾中日出，不是初夏有风的明亮白昼 |
| 目标画幅 4:5 | FAIL | 实际约 4:3 横幅 |
| `full` 提示词哈希绑定 | UNKNOWN | 未有可核实的精确文本字段绑定回执 |
| 模型/种子/锚点角色 | UNKNOWN | 实际 ImageGen 后端不披露 |
| `compact-v1` 生成 | NOT_RUN | 题材冒烟测试失败后停止 |

**风格评分：四项均 `null`；加权分 `null`；有效 A/B 配对数 = 0。** 不得将本次生成归入 `full` 或 `compact-v1` 的可归因性能测量，因为实际输入绑定不可核实。不能据此声称 `compact-v1` 提升或退步，更不能将失败归因于版权或服务提供方审核。

## 对后续执行的约束

本次重现了历史已知的 **跨任务/会话内容污染疑似现象**（题材改成女子但返回旧港口）。这只是可观察到的错误路由表现，无法从回执证明内部根因。

后续必须使用可明确提交图片专用 prompt、隔离上次实验上下文、保留模型/参考像素/尺寸回执的宿主再做视觉 A/B。如果仍只能通过 ChatGPT 会话上下文推断提示词，应把结果称为探索性 smoke，不叫受控 A/B。初步验证必须先过 `subject_class`，失败即停止，不继续生成并虚构结果。

**决策：NO_PROMOTION。** 保留 `compact-v1` 为可选、未验证画法；`full` 和原始 `regional-p0` 默认不变。本轮没有 ComfyUI、其他生图后端或新增收费 API 调用。
