# P0 · 后端资格检查与第二次输出路由失败

**日期：2026-11-10** · **状态：BLOCKED_HOST_CAPABILITY / NO_VALID_ARTWORKS**  
[预注册实验计划](P0-regional-brushwork-plan.json) · [第一次执行记录](P0-2026-11-10-execution.md)

## 本次复试的实际证据

实验目标是三项题目（港口、阳伞人物、干草堆），每项 `baseline` 与 `regional-p0` 各一张，需完整固定提示词、同一模型、真实风格锚点、画幅和评审标准。

本次只针对 MOR-01 做了 **2 次生成调用**，返回均为**带对照表和虚构评分的信息图**，非独立绘画：

| 调用记录 | 实际图像 | SHA-256 | 结论 |
|---|---|---|---|
| `d27dd348-869f-4bd5-a3db-dca4cf808c3e` | PNG 1536×1024 | `dec9e08bf2bd61a906c49bd41d4f975190c2b9a2ec8f439abe687081d77c9d85` | REJECTED：报告图、画幅不匹配 |
| `f43ca4be-a3c2-4dcf-8179-9b40fbe6acab` | PNG 1536×1024 | `5034a68d97532c40961fbe36be7904e6ab531774e404c4264602dac68966636c` | REJECTED：报告图、画幅不匹配 |

原预期是 4:3 港口单幅油画；实际均为 3:2 排版报告。图中分数完全无真实 A/B 支撑，**不能引用为实验数据**。本次有效绘画 = 0，P0 效果无可计算值；停止后续调用，默认版不变。

## 能解释和不能解释的事情

- 现有 `monet.py prepare --brushwork-variant` 能生成明确不同的实验指令，过去 21 项离线回归已通过；这是**输入编译**证据，不是生图后端接收证据。
- 实际调用途径未提供可证明的直接提示词字段绑定、锚点图片字节绑定、多参考角色校验、模型版本和精确画幅控制。
- 输出内容偏向“实验报告”说明存在调用上下文与任务目标的**路由失配**；上下文污染是合理怀疑，但没有证据能够唯一确认根因。
- 这是输出路由失败，**不是**已确认的版权审核拒绝，也不是 P0 笔触效果失败。

## 直接防范措施

新增纯标准库工具 `host_qualification.py` 和 11 项单元测试。资格检查要求：显式提示词传递、已校验的原作风格锚点真实送达、参考角色可核验、画幅控制、后端模型身份、真实图片输出与调用回执。未知条件按不支持处理；额外付费后端未经批准也不通过。

运行示例：

```bash
python3 benchmarks/original-paintings-v1/host_qualification.py \
  benchmarks/original-paintings-v1/rounds/P0-current-host-capabilities.json
python3 -m unittest discover -s benchmarks/original-paintings-v1 -p test_host_qualification.py -v
```

本次能力快照为 `BLOCKED_HOST_CAPABILITY`。检查通过只证明后端符合**实验前置条件**，生成后仍需检验图像是否单幅、内容与画幅是否正确、是否存在伪纹理，并以原作对照评分。

## 后续行动

不应再次用当前未验证路径连续输出六张无效图片。换用**支持明确原始提示词、可验证上传参考图、可记录调用与输出**的生图宿主，在真正成功生成一张 MOR-01 的单幅样本且通过硬门后，再执行六张 A/B。**本项目没有自动使用收费 API 或租用 GPU，亦未改变正式 Skill 默认画法。**
