# 原始证据索引

代码链接固定到经 commits 接口核对的提交，不依赖 main 的后续变化。源码证明实现行为，不证明图像质量；论文实验结论也不直接等于本项目的实测结果。

## S1 · InstantStyle：作者提出的机制、适用范围与实验

- [原始来源 1](https://arxiv.org/html/2404.02733v2)

## S2 · 全局特征相减；IPAdapterXL.generate 参数与批次

- [原始来源 1](https://github.com/instantX-research/InstantStyle/blob/6b40588e263c958653353ec24eb7eb990cfa3da7/ip_adapter/ip_adapter.py#L154-L169)
- [原始来源 2](https://github.com/instantX-research/InstantStyle/blob/6b40588e263c958653353ec24eb7eb990cfa3da7/ip_adapter/ip_adapter.py#L241-L324)

## S3 · IPAdapterPlusXL 的 patch 表示及示例

- [原始来源 1](https://github.com/instantX-research/InstantStyle/blob/6b40588e263c958653353ec24eb7eb990cfa3da7/ip_adapter/ip_adapter.py#L371-L399)
- [原始来源 2](https://github.com/instantX-research/InstantStyle/blob/6b40588e263c958653353ec24eb7eb990cfa3da7/infer_style_plus.py)

## S4 · Diffusers 原生逐块 IP-Adapter scale

- [原始来源 1](https://github.com/huggingface/diffusers/blob/8c54b38fea3d624d23d0e43c0c96037f080a79f9/src/diffusers/loaders/ip_adapter.py#L516-L568)

## S5 · 参考注意力 skip 与加法合入

- [原始来源 1](https://github.com/instantX-research/InstantStyle/blob/6b40588e263c958653353ec24eb7eb990cfa3da7/ip_adapter/attention_processor.py#L339-L393)

## S6 · 风格图与 Canny 内容图分离的真实示例

- [原始来源 1](https://github.com/instantX-research/InstantStyle/blob/6b40588e263c958653353ec24eb7eb990cfa3da7/infer_style_controlnet.py#L26-L55)

## S7 · InstantStyle-Plus 的三类条件；默认关闭的额外引导

- [原始来源 1](https://arxiv.org/html/2407.00788v1)
- [原始来源 2](https://github.com/instantX-research/InstantStyle-Plus/blob/11b2d96e0af6290b5ee503f8b85da3eeefe52732/infer_style.py#L214-L248)

## S8 · CSGO 的独立内容／风格输入及专用配置

- [原始来源 1](https://github.com/instantX-research/CSGO/blob/fefec09cf680d9796b92a64282ceb12501b9f977/infer/infer_CSGO.py#L19-L84)

## S9 · ControlNet 时段门控和残差条件缩放

- [原始来源 1](https://github.com/huggingface/diffusers/blob/8c54b38fea3d624d23d0e43c0c96037f080a79f9/src/diffusers/pipelines/controlnet/pipeline_controlnet_sd_xl.py#L1380-L1387)
- [原始来源 2](https://github.com/huggingface/diffusers/blob/8c54b38fea3d624d23d0e43c0c96037f080a79f9/src/diffusers/pipelines/controlnet/pipeline_controlnet_sd_xl.py#L1486-L1524)

## S10 · Skill 的固定配方、参考图、验收与确定性填槽

- [原始来源 1](https://github.com/threerocks/hand-drawn-styles/blob/5a2f91fcbd32694a6caa9c7d09b2b3bad2666bc3/SKILL.md#L8-L22)
- [原始来源 2](https://github.com/threerocks/hand-drawn-styles/blob/5a2f91fcbd32694a6caa9c7d09b2b3bad2666bc3/scripts/render_prompt.py#L432-L446)

## S11 · mono-color 的视觉规范与独立素材许可

- [原始来源 1](https://github.com/yanliudesign/mono-color-skill/blob/c8ff70597ddedcd65f21a0b528f6a70c35690b0a/SKILL.md)
- [原始来源 2](https://github.com/yanliudesign/mono-color-skill/blob/c8ff70597ddedcd65f21a0b528f6a70c35690b0a/ASSET-LICENSE.md)

## S12 · Diffusers 关于随机性与跨环境复现的说明

- [原始来源 1](https://huggingface.co/docs/diffusers/en/using-diffusers/reusing_seeds)

## S13 · GitHub 官方许可证说明

- [原始来源 1](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

## R1 · 本项目已有参考集统计

- [原始来源 1](../../reference-set/stats.json)

## 复核符号检查

单独取得 S2 对应的固定版本文件后运行（脚本不会联网或加载模型）：

```bash
python3 checks/audit_upstream_contract.py --source-file /path/to/ip_adapter.py --out /tmp/contract-audit.json
```

脚本仅接受记录的 SHA-256。输出的五项确认中，两项是旧封装风险的复现，绝不是图像质量验收。
