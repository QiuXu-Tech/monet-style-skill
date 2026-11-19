# Monet Style · 0.5.0-alpha.2

**研究指导升级版：已将九篇原作研究和1875人物专题转化为绘画决策、按题材调用的指令和原作对照评审。新版真实出图质量尚待验证。**

默认仍为1880s，默认图像锚点仍为 `antibes-1888`。本版支持准备提示词、评审返回图、原作研究，以及在当前会话授权下使用已有生图工具。不会因为安装Skill就获得模型或自动启动测试。

## V3-W02：笔触构形修订

针对实际返回的花园、河流两幅图“色彩好看但画风和笔触不像莫奈”的问题，将默认绘画语言改为**用相邻色笔构成形体、光影与边缘**，避免在光滑数字插画上均匀铺设装饰性短笔。旧核心保持原样，作为 `research-v3-previous` 对照配置；水面模块和默认锚点未修改。

```bash
python3 scripts/monet.py prepare --request examples/river-w02.json --text-only --profile research-v3-previous --out /tmp/w02-old
python3 scripts/monet.py prepare --request examples/river-w02.json --text-only --profile research-v3 --out /tmp/w02-new
```

需在两个独立生图聊天里分别使用上述输出；当前本项目研究聊天不生图。原图W01不是冻结编译结果，不能据它与W02的差异宣称严格单变量实验。[定向实验记录](../../docs/V3-W02-paint-construction-2026-11-19.zh.md)。

## 本次升级

- 保留大形、姿态、遮挡与主平面，允许局部笔触和次要边缘断续。
- 按结构、材质、光照、距离、视觉作用和画面节奏选择笔触；同一材质内部也可以不同。
- 将光照对色彩、边缘和细节可见度的影响连在一起，取消默认“必须有雾”的要求。
- 按尺度和作用分配人物、花卉、天空等区域的细节，避免全面精修或全面模糊。
- 区分可见笔迹、表面起伏和覆盖历史，不再以统一厚涂代表莫奈。
- 花园、水面、人物、建筑、雪景、海岸六个模块按需选用，最多三个，不全部塞入提示。
- 保留旧版 `legacy-v2` 与独立P0实验；新版不是P0已经验证成功的晋级。

原作证据及例外见[artwork-evidence.md](references/artwork-evidence.md)，具体画面决策见[painting-language.md](references/painting-language.md)。

## 在对话中使用

当前项目研究会话保持**只准备提示词、由用户另开聊天生图**。例如：

> 使用 $monet-style，为晴朗午后的原创花园场景准备一条完整提示词，有两名交谈的人物；只输出纯文本，我会另开对话测试。

评审时发送实际图片：

> 使用 $monet-style，对照已经核实的对应原作评审这张图，重点看花群、脸手和天空的完成程度，不生图。

在其他允许实际生图的会话，可以请求创作或转绘。Skill会按当前工具能力执行，不伪造附件或模型参数。若用户只要提示，直接放在对话中，不自动交付TXT/ZIP。

## 安装与范围

将完整 `monet-style`目录放入宿主支持的Skill目录，勿只复制SKILL.md。常见路径包括Codex的 `~/.agents/skills/monet-style/` 与Claude Code的 `~/.claude/skills/monet-style/`；也可按宿主官方说明使用项目级目录。刷新或重新打开Skill列表确认发现情况。

普通文字编译与一致性检查需要Python 3.10+，无需GPU。cleanup预处理另需Pillow（见requirements.txt）。安装不改变用户全局设置，不安装图像模型。

已研究1870s、1880s和部分1890s作品，不等于已有各时期的完整生成预设。晚期大型睡莲尚未获得本批研究覆盖。现代建筑、夜景等迁移效果也仍需实际图片检验。

## 文本编译

以下从Skill目录执行，输出目录必须是新的任务目录：

```bash
python3 scripts/monet.py check
python3 scripts/monet.py prepare --request examples/garden-figures.json --text-only --out /tmp/monet-garden-001
```

将`prompt.txt`完整正文复制到对话中；文件是内部可追踪产物，不代表默认要给用户文件下载。`job.json`独立保存原始请求、选用模块、原作未附状态、正文及文件哈希。脚本没有生成图片。

新增请求字段：

| 字段 | 用途 |
|---|---|
| `subject_modules` | 选择0—3个已在请求里存在的题材：garden / water / figures / architecture / snow / coast |
| `painting_notes` | 最多5条简短的场景关系，补充核心和模块没有表达的区域要求 |

其余字段沿用：`request`、`must_keep`、`must_avoid`、`aspect_ratio`、`mode`、`anchor_id`、`content_image`、`cleanup`。参考[花园人物示例](examples/garden-figures.json)和[河岸建筑示例](examples/river-evening.json)。不存在的内容不要为了使用模块而添加。

## 参考与系列

参考受控路径需要真实图片像素传入可用工具：

```bash
python3 scripts/monet.py fetch --anchor antibes-1888
python3 scripts/monet.py prepare --request examples/train.json --out /tmp/monet-train-001
```

两幅锚点继续使用固定来源与SHA-256校验；默认Antibes1888，显式备选Pourville1882。锚点目录和图片字节未改变。源码包不捆绑完整研究图片集，不依赖外层研究目录才能编译。

`prepare`只确认本地准备，不证明已附图。真实执行与逐角色交付证据见[host-tools.md](references/host-tools.md)。系列使用`--lock previous-run/style-lock.json`；规则或版本变化会拒绝静默续接。题材模块选择可随新内容变化，模块库自身的SHA受锁定。

## 旧版与实验隔离

```bash
python3 scripts/monet.py prepare --request examples/train.json --text-only --profile legacy-v2 --out /tmp/monet-legacy-001
python3 scripts/monet.py prepare --request examples/train.json --text-only --profile legacy-v2 --brushwork-variant regional-p0 --out /tmp/monet-legacy-p0-001
```

旧核心原样保存在`style-contract-v2.json`；P0叠加文本未改变。新题材模块和painting_notes适用于research-v3和research-v3-previous。完整历史任务仍以当时提交和锁为准，新版本锁不假装与旧版本相同。旧prompt含历史元数据包装；本轮benchmark不把该包装伪称为清洁生成正文。

## 转绘与纹理清理

只有真实内容图才可使用`mode: restyle`。内容图控制身份/布局，style-only参考控制画法。相对图片路径按request.json所在目录解析；私有图不自动进入仓库。

[clean-remake](references/clean-remake.md)保留为可选工具：先诊断具体纹理失败，再决定是否准备结构图和可选光色辅助。辅助图不是成品，不能以全图模糊换取鳞纹减少；需要用户要求及宿主角色支持。原图比例与请求画幅不匹配时仍拒绝。

[本地ComfyUI适配器](references/explicit-comfyui.md)继续默认dry-run，仅供明确要求的已配置环境。此升级没有进行真实GPU推理或图像生成。

## 评审与验证

[review.md](references/review.md)规定整幅—区域—局部审看、内容与原创性门禁、原作定义锚点，以及笔触30%/色彩30%/空气氛围30%/机械鳞纹10%。原作对应各维10分，人评与模型评分独立；未知门禁和未查看图片不计算有效总分。

`monet.py review`核对记录一致性并登记观察，不自动判断画风，也不计算四维分数。项目另有原作对照协议的评分记录校验器。工程测试通过仅证明规则、文件和流程行为；实际美术质量需要用户另开会话出图并回传。

本版依然是alpha。历史R001、P0及其他实验失败记录保留；本版没有新的生成图、虚构分数或稳步提升声明。代码与原创文档采用MIT，第三方图片遵循各自授权。
