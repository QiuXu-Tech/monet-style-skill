# P0 · 区域笔触实验（未实测）

**状态：NOT_VISUALLY_BENCHMARKED。** 依据此前三张独立画作的人工观察：港口水面有相似细碎鳞纹；人物画天空、衣裙、草地的笔触过于同质；干草堆的光影块面仍可改进。分数是视觉诊断，不是经过固定宿主的 Skill A/B。

## 单一假设

只在原有画法规则之后附加 [区域笔触说明](regional-brushwork-p0.txt)，按材质、深度组织笔触与留白，可能改善机械纹理，同时不损害内容、色彩及空气感。

## 对照

固定相同请求、宿主、模型、宽高比、原作锚点、光色预设和 cleanup；只切换 `--brushwork-variant baseline` 与 `regional-p0`。两组不同 style lock，**不得混作同一系列**。原画比较使用现有 [三原作协议](https://github.com/QiuXu-Tech/monet-style-skill/blob/main/benchmarks/original-paintings-v1/README.zh.md)，跨年代任务应标为 `OUT_OF_PROFILE_EXPLORATORY`，不能证明 1880s 预设覆盖 1870s 与 1890s。

评分：笔触 30%、色彩 30%、氛围 30%、鳞纹控制 10%；完整主体、天气、单幅画格式为硬门。保留所有首轮样本与真实调用记录，未出图记 `NOT_RUN`。如鳞纹下降但空气感、主体或色彩退化，不得晋级。严禁使用人工编造的报告图替代生成样本。
