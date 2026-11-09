# Clean Remake Image Skill：莫奈风格纹理污染研究

**日期：2026-11-09**  
**状态：REFERENCE_STUDIED / PREPROCESS_PROBED / GENERATION_NOT_RUN。** 当前仅纳入技术参考，不直接导入第三方代码、不修改 Monet Skill 的运行规则。

## 研究对象

- 上游项目：[kevinchin12/clean-remake-image-skill](https://github.com/kevinchin12/clean-remake-image-skill)，固定提交 [6bf35bcd045a119bdea62153345ecd34fc005467](https://github.com/kevinchin12/clean-remake-image-skill/tree/6bf35bcd045a119bdea62153345ecd34fc005467)（SKILL.md 为 v1.1.0）。
- 已审阅 [SKILL.md](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/SKILL.md)、[构图生成脚本](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/scripts/make_composition_map.py)、[参考图路由](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/references/reference-routing.md)、[重绘任务单](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/references/rebuild-brief.md)、[审核脚本](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/scripts/make_review_sheet.py)、[测试集](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/tests/test_scripts.py) 与 [MIT 许可](https://github.com/kevinchin12/clean-remake-image-skill/blob/6bf35bcd045a119bdea62153345ecd34fc005467/LICENSE)。

## 核心机制与局限

上游采用 **Controlled Information Bottleneck**：先冻结必须保留的主体、位置、宽高比与交互关系，再根据污染图制作简化构图参考，以新的干净绘制过程替换污染像素，最后审查输出。**它不是滤镜、逐像素修复器或自带模型的生图平台。**

- **Quantized composition map**：先预模糊，再用 Pillow 无抖动量化。默认建议约 30 色，参考值 `blur-long-edge-ratio=0.0008`。它主要保留结构、位置与大色块；色数过少会把连续光色切成硬块。
- **Gaussian support**：可选 `blur-long-edge-ratio=0.005` 的低频辅助，保留整体光照、空气与色温。高斯图本身不等于完成品，也可能模糊掉台阶、灯柱等关键结构。
- **角色隔离**：构图图只管空间关系，Gaussian 图只管大尺度光色，独立的干净风格/身份参考只管被允许迁移的特征。若宿主不支持多张参考图的真实角色隔离，不能仅凭提示词认为隔离已经生效。
- **拒收门槛**：构图、身份、语义、画面完成度和受保护内容五项分开验收。脚本记录的 surface activity 是残差诊断，**不是艺术质量分数**，过度磨平也可能降低该数值。
- **污染回流控制**：原始脏图默认用于诊断与比对，而不直接作为最终生图的主要参考；否则机械重复鳞纹可能被模型再学习和放大。

## 为什么对 Monet Style 有用

此前生成图片中的“鳞纹”更像**重复且机械的细小伪油画纹理**，而不应未经鉴定就称为物理摩尔纹。需要减少的是这种同质微纹理，保留的是莫奈式的色彩交融、空气透视、选择性模糊边缘、灯光漫散与有节奏的粗细笔触。

建议下阶段拆为三种职责：

1. **内容与硬约束**：单幅夜景、一盏可见路灯、潮湿台阶和远方现代建筑。
2. **空间与光色参考**：经审查的构图图；必要时可额外引入低频光色图。原生成的双联画是失败布局，不能作为必须保留的构图。
3. **绘画语言参考**：Monet Style 已核实原作及画法契约，独立于污染图，避免把参考画里的房屋、帆船等主体搬过来。

重点避免三种退化：把量化图的硬边重绘成“印象派块状拼贴”；把 Gaussian 结果直接交付成统一模糊图；把原本漂亮的朦胧空气感与假鳞纹一起删掉。

## 本轮小试验（仅离线预处理）

使用对话中已生成的双联画**右侧夜景裁剪**作测试材料，本地以 Pillow **独立复现同类处理方法**，生成无抖动 24/30/48 色量化参考及 0.005 比例的低频光色参考。30 色图能保留一盏灯、台阶走势与蓝紫/暖金色域，但出现偏硬的边界；Gaussian 参考更能保留漫射灯光和空气感，但削弱台阶轮廓。这些诊断图与原对话图像未上传公共 GitHub。

**没有安装或执行上游完整 Skill；没有用生成模型进行清洁重绘、真实 A/B、人工盲评或稳定性验收。** 因此不得据此断言哪条方案更好。

## 后续最小验证（NOT_RUN）

在支持该类图片输入的固定生图后端上，将同一完整任务分别执行：A 直接编辑污染图；B 审核后的构图图 + 独立莫奈画风参考；C 仅当宿主支持可信的多参考角色时，在 B 之外添加低频光色图。每组先重复两次，**上限六张**，评审鳞纹、夜景空气感、光色连续性、单灯/台阶/建筑内容合规和参考图内容泄漏。若出现额外路灯、错误拼版或画面被完全磨平，视为不合格。

只在真实测试有证据后考虑添加清洁重绘机制；上游 MIT 源码引用须保留作者与许可，原作和生图服务授权需分别核对。