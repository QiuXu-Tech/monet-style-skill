# 莫奈原作逐幅研究档案

本目录用于长期保存**每幅莫奈原作的独立分析报告**，与生成器代码、P0/P1/P2 等提示词实验分开。每篇报告包括可查的馆藏数据、区域笔触观察、空间/光色关系、对 Monet Style Skill 的候选启发、参考泄漏风险和来源 URL。**没有真实出图，就不填写生成分数或宣称改善。**

## 本系列

| 次序 | 原作 | 年代 | 馆藏 | 报告 |
|---|---|---|---|---|
| 01 | 《印象·日出》 / *Impression, soleil levant* | 1872 | Musée Marmottan Monet · 4014 | [研究 01](01-impression-sunrise-1872.zh.md) |
| 02 | 《普尔维尔的悬崖》 / *Cliffs at Pourville* | 1882 | National Gallery of Art · **1985.64.27** | [研究 02](02-cliffs-at-pourville-1882-nga.zh.md) |
| 03 | 《昂蒂布的园丁之家》 / *Gardener's House at Antibes* | 1888 | Cleveland Museum of Art · **1916.1044** | [研究 03](03-gardeners-house-antibes-1888-cma.zh.md) |

**历史专题补录：** [1875《撑阳伞的女人》原作研究](woman-with-parasol-1875-reference.zh.md)；其先前 P1/P2 试验记录仍在各自的实验日志里。

## 统一记录标准

1. **事实 / 视觉观察 / 工程假设三层分离。** 美术馆记载、技术分析可以引用为证据；从图像看到的笔触方向、疏密、风与光的关系作为视觉解释；如何通过 prompt 复现这些特征只作待测假设。
2. **同名作品明确区分馆藏。** 尤其 NGA 的 `Cliffs at Pourville`（1985.64.27）与芝加哥的 `Cliff Walk at Pourville`（1933.443）不能混用图像或技术研究。
3. **原作 10 分仅为该作品的局部风格校准。** 不等于要求模型复制该作品的人物、船只、地形、构图、签名，也不意味着不同时期画法同质。
4. **图像及权利分离。** 不在 Markdown 内再次上传馆藏原图；链接官方馆藏和现有 `research/reference-set/`。图片的授权以逐件许可证为准，不因代码 MIT 自动转为 MIT。
5. **实验和研究分离。** 默认画法不会仅因新增原作观察而更新；新提示词需预登记、真实生成和原作对照回归。

后续每研究一幅作品，就新增一篇独立 Markdown 并更新本索引。原始研究目录仍见 [research/artworks.md](../artworks.md)。
