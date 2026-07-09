# 易经虚拟宇宙建模总纲

## 1. 目标

本文件定义 `edgeWorld / 易之世界` 的顶层建模路线。项目目标不是把《易经》作为装饰符号贴到地图或 UI 上，而是把《易经》的结构、变化、循环、因果与收敛思想转化为一个可运行、可验证、可扩展的虚拟宇宙。

`edging` 是该宇宙的运行引擎。它的职责不是单纯生成地形，而是持续仲裁：

- 空间如何生成。
- 时间如何推进。
- 能量如何分配。
- 熵如何积累与收敛。
- 实体如何生灭。
- 玩家如何通过“降神”注入变量。
- 世界如何在三才循环中进入下一纪元。

## 2. 建模原则

### 2.1 易经不是题材，而是操作系统

所有核心系统必须至少映射到一个易学结构：

| 易学结构 | 引擎含义 | 游戏表现 |
| --- | --- | --- |
| 太极 | 世界整体状态 | 宇宙总能量、总熵、纪元状态 |
| 两仪 | 阴阳二气 | 能量分配、生命倾向、环境偏性 |
| 四象 | 时间节律 | 生发、鼎盛、收敛、寂灭 |
| 八卦 | 空间基元 | 地貌、气候、资源、危险倾向 |
| 六十四卦 | 区域/命运组合 | 卦域、事件池、主线定数 |
| 爻变 | 局部状态突变 | 玩家行为、事件触发、区域变卦 |
| 综卦 | 反向视角 | 镜像区域、历史回响、反事实线 |
| 错卦 | 对立潜能 | 敌对生态、隐藏势力、逆命事件 |
| 八宫 | 谱系归属 | 地域族群、势力传承、长期演化关系 |

### 2.2 先形式化，再美术化

建模顺序必须是：

1. 定义概念。
2. 定义数据结构。
3. 定义状态转移规则。
4. 编写可运行原型。
5. 编写验证测试。
6. 可视化观察。
7. 接入 Swift / Metal 渲染。

不能先做视觉效果，再反向解释为易经规则。这样会导致世界缺少内在一致性。

### 2.3 所有玄学都必须有可计算影子

“命运”“变数”“悟道”“天命反噬”等概念都可以保留文学表达，但引擎内部必须落成数据：

- `fateVector64`：64 维行为/命运向量。
- `entropyTrace`：玩家或区域造成的扰动轨迹。
- `mainHexagram`：当前定数主卦。
- `changedLines`：由行为触发的爻变。
- `convergencePressure`：世界要求收敛的压力。
- `eraTransitionScore`：纪元更迭评分。

## 3. 宇宙分层模型

### 3.1 纪元层：Era

纪元是最高规则集。当前规划为：

| 纪元 | 含义 | 模拟倾向 |
| --- | --- | --- |
| 周 | 新生、末法、探索 | 低能量、低文明、高遗迹密度 |
| 连仙 | 鼎盛、仙法、扩张 | 高能量、高文明、高技术/法术密度 |
| 灭世 | 崩坏、战争、重置 | 高熵、高冲突、高收敛压力 |

纪元决定：

- 全局能量上限与可用率。
- 熵增长速度。
- 文明密度。
- 生物强度。
- 遗迹与资源分布。
- 收敛事件触发阈值。

### 3.2 卦域层：Hexagram Region

世界宏观空间由 8x8 卦域构成，共 64 个区域。

- `x` 方向映射下卦。
- `y` 方向映射上卦。
- 下卦决定基础地貌。
- 上卦决定外部影响、气候、事件倾向。

每个卦域至少包含：

```text
RegionState
- regionId
- hexagramValue
- lowerTrigram
- upperTrigram
- palace
- terrainRule
- entropy
- stability
- resourceBias
- dangerBias
- eventBias
```

### 3.3 地块层：WorldTile

地块是可采样、可渲染、可交互的最小空间单位。

```text
WorldTile
- regionId
- localX / localY
- hexagramValue
- height
- moisture
- temperature
- yinQi
- yangQi
- entropy
- biome
```

约束：

- `yinQi + yangQi <= tileEnergyLimit`
- `biome` 是推导结果，不是输入标签。
- `entropy` 不是随机噪声，而是区域规则、时间、事件和行为共同影响的状态。

### 3.4 实体层：Entity

实体包括：角色、NPC、生物、植物、遗迹、势力节点、灵物、灾害。

最小组件：

```text
Entity
- id
- kind
- position
- qi
- lifecycle
- fate
- behaviorState
```

生命周期：

1. 初生。
2. 鼎盛。
3. 衰败。
4. 消亡。

实体死亡不是删除，而是能量回流：

```text
entityEnergy -> tileEnergy -> regionEnergy -> latentWorldEnergy
```

### 3.5 玩家层：Player / Avatar / GodDescent

玩家不是普通实体。

| 概念 | 含义 |
| --- | --- |
| Player | 外部操作者，来自世界之外 |
| Avatar | 世界内角色，是实体 |
| GodDescentSession | 玩家短时接管角色的降神窗口 |

降神的核心效果：

- 改变角色行为向量。
- 注入熵。
- 触发爻变。
- 改写定数边界，但不直接绕过世界仲裁。

## 4. 宇宙运行循环

`edging` 引擎每个逻辑 tick 执行：

```text
1. 推进 WorldClock
2. 应用四象阶段修正
3. 更新区域熵与稳定度
4. 处理实体能量交换
5. 推进实体生命周期
6. 计算玩家降神影响
7. 触发爻变、事件、收敛
8. 结算死亡、诞生、资源再分配
9. 导出可渲染世界快照
```

第一阶段不需要完整服务器模拟，可以先在 Python 原型中完成规则闭环，再移植 Swift 运行时子集。

### 4.1 大衍变数算法

`大衍之数五十，其用四十有九` 是 `edging` 的变数生成原则。它不是普通随机数，而是可追溯的象数随机：

```text
一变 = 分二 + 挂一 + 左扐 + 右扐
三变 = 一爻
六爻 = 一卦
本卦 + 变爻 = 变卦
```

函数边界：

```text
cast_change(activeCount, context) -> ChangeCast
cast_line(context, lineIndex) -> LineCast
cast_hexagram(context) -> HexagramCast
```

抽象含义：

- `分二`：世界状态分为阴阳两势。
- `挂一`：观察者、玩家或天命介入，形成三才。
- `左扐 / 右扐`：阴阳两侧不能被四象整除的余差。
- `归奇于扐`：余差被保存为闰，成为熵和变数来源。
- `三变成爻`：局部状态稳定为老阴、少阳、少阴、老阳之一。
- `六爻成卦`：形成一次完整的世界判定。

当前实现位置：`engine/dayan.py`。

### 4.2 四象数值编码

`edging` 的四象编码采用：

| 四象 | 编码 | 对应传统爻值 | 含义 |
| --- | ---: | ---: | --- |
| 太阴 | `0` | `6` | 老阴，阴极而变 |
| 少阳 | `1` | `7` | 阳初生，不变 |
| 少阴 | `2` | `8` | 阴成，不变 |
| 太阳 | `3` | `9` | 老阳，阳极而变 |

因此爻值到四象编码的映射为：

```text
6 -> 0  太阴
7 -> 1  少阳
8 -> 2  少阴
9 -> 3  太阳
```

这套编码不是按传统爻值自然排序，而是按本项目定义的四象状态位排序。

## 5. 第一阶段建模范围

第一阶段只做“可验证宇宙胚胎”，不要同时做完整 RPG。

### 5.1 必须完成

- 八卦基础规则表。
- 六十四卦区域生成。
- 固定 seed 的确定性世界生成。
- 四象时间推进。
- 地块高度、湿度、温度、阴阳气、熵。
- 生物群落推导。
- 区域摘要导出。
- 单元测试验证关键约束。

### 5.2 暂不做

- 完整 NPC AI。
- 战斗系统。
- 网络同步。
- 真实经济系统。
- 大规模持久化。
- 复杂任务系统。
- 真实多人服务器。

### 5.3 当前代码位置

- Python 易学数学层：`engine/mathEdge.py`
- Python 大衍变数层：`engine/dayan.py`
- Python 世界原型层：`engine/world_engine.py`
- Python 验证测试：`tests/test_world_engine.py`
- Swift / Metal 渲染原型：`edge-world Shared/Renderer.swift`
- 世界设计文档：`doc/edging_world_engine_model.md`

## 6. 专业工具与 Skill 使用矩阵

### 6.1 建模与规划

| 目标 | 工具 / Skill | 用法 |
| --- | --- | --- |
| 总体路线 | `software-development/plan` | 生成阶段计划、文件路径、验证标准 |
| 假设验证 | `software-development/spike` | 快速验证单个模型问题 |
| 可测试建模 | `software-development/test-driven-development` | 规则先写测试，再实现 |
| 问题定位 | `software-development/systematic-debugging` | 模拟结果异常时找根因 |

### 6.2 可视化与表达

| 目标 | 工具 / Skill | 用法 |
| --- | --- | --- |
| 系统架构图 | `creative/architecture-diagram` | 画引擎层级与数据流 |
| 概念草图 | `creative/excalidraw` | 画三才、四象、八卦循环 |
| 信息图 | `creative/baoyu-infographic` | 输出面向展示的视觉说明 |
| 交互式图形 | `creative/p5js` | 快速观察卦域/熵场/能量流 |

### 6.3 数据探索

| 目标 | 工具 / Skill | 用法 |
| --- | --- | --- |
| 参数探索 | `data-science/jupyter-live-kernel` | 交互式观察地形/熵分布 |
| Python 脚本 | `terminal` / `execute_code` | 跑原型、导出 JSON、做统计 |
| 单元测试 | `python3 -m unittest` | 当前环境无 pytest，优先标准库测试 |

### 6.4 工程落地

| 目标 | 工具 / Skill | 用法 |
| --- | --- | --- |
| Swift/Metal 接入 | Xcode / `xcodebuild` | 把 Python 规则移植到客户端 |
| 代码审查 | `software-development/requesting-code-review` | 阶段性检查复杂度、安全与质量 |
| 多代理开发 | `autonomous-ai-agents/codex` 或 `claude-code` | 后续可并行拆分 Swift、Python、文档任务 |

## 7. 建模验证标准

### 7.1 正确性

- 同一个 seed 必须生成完全一致的世界。
- 64 个卦域必须覆盖完整 8x8 网格。
- 区域 `x/y` 到上下卦的映射必须稳定。
- `yinQi + yangQi` 不得超过预算。
- 四象阶段推进必须循环。

### 7.2 表达性

- 不同卦域必须产生可观察差异。
- 下卦变化应明显影响基础地貌。
- 上卦变化应明显影响气候/事件/危险倾向。
- 高熵区域应产生混乱、危险或异常表现。
- 低熵区域应更稳定、更可预测。

### 7.3 可玩性

- 玩家行为必须能改变世界状态。
- 降神必须有代价，至少表现为熵注入或爻变风险。
- 世界必须有收敛机制，不能无限发散。
- 定数和变数必须能反馈到角色体验。

## 8. 下一步任务

### 8.1 文档任务

1. 在本文件基础上拆出 `宇宙公理表`。
2. 定义 `八卦 -> 参数` 的正式规则表。
3. 定义 `六十四卦 -> 事件倾向` 的第一版映射。
4. 定义 `玩家行为 -> 64 维向量` 的初始维度。

### 8.2 Python 原型任务

1. 为 `world_engine.py` 增加 `eventBias` 和 `resourceBias`。
2. 增加 `apply_descent(session)`，模拟降神注入熵与爻变。
3. 增加 `WorldSnapshot`，作为 Swift/Metal 读取的数据边界。
4. 导出 `models/terrain_rules.json`。

### 8.3 Swift 接入任务

1. 新建 `edge-world Shared/WorldEngine.swift`。
2. 移植 `Trigram`、`HexagramId`、`WorldClock`、`TerrainRule`。
3. 用固定 seed 替换当前 `UInt32.random`。
4. 让 `Renderer.swift` 消费 `WorldTile`，而不是内部随机生成 `Cell`。

## 9. 当前推荐路线

最近 3 个开发闭环建议如下：

1. **规则表闭环**：把八卦/地形/气候/熵/阴阳气规则整理成 JSON，并用测试验证。
2. **降神闭环**：实现一次玩家行为如何改变爻、卦、熵和事件倾向。
3. **渲染闭环**：Swift 读取或复刻 Python 规则，用固定 seed 显示 8x8 卦域世界。

完成这三个闭环后，`edging` 才算真正从“设定文档”进入“可运行宇宙胚胎”。
