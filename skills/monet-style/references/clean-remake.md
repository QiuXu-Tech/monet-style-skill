# Monet Style 中的 clean-remake 路线

此路线用于：

- 图片大体内容和氛围已接近目标；
- 但表面充满细碎、机械重复的假油画纹理、鳞纹、脏渐变或过锐化光晕；
- 希望保留莫奈式朦胧感，而不是把整幅图简单磨糊。

## 请求字段

```json
{
  "mode": "restyle",
  "content_image": "night-source.png",
  "cleanup": {
    "enabled": true,
    "route": "quantized+gaussian",
    "colors": 30,
    "max_side": 1536,
    "map_blur_long_edge_ratio": 0.0008,
    "gaussian_blur_long_edge_ratio": 0.005
  }
}
```

- `route = quantized`：只生成结构图，适合先最大限度保结构。
- `route = quantized+gaussian`：在结构图之外增加低频光色辅助，更适合保留夜景的光晕和空气感。
- `colors`：结构图的量化色数。一般从 30 开始；小主体或复杂层次可以提高到 48。

## 角色划分

1. **style-only anchor**：只给莫奈画法。
2. **cleanup-structure map**：只给布局、主体数量、遮挡、地平线和大色块。
3. **cleanup-lighting support**：只给光照、空气、色温连续性。
4. **原始 content image**：仅分析/复核；不要再次复制其脏纹理，除非宿主因工具限制必须以受控方式附上。

## 重要边界

- 结构图不是最终画。
- Gaussian support 不是最终画，也不等于“莫奈式朦胧”。
- cleanup 路线不自动证明更好；只有真实生成并经 review 通过，才能说某次结果更合理。
- 若宿主不能清楚区分多参考图角色，则宁可停用 cleanup，也不要把所有图一股脑附上。