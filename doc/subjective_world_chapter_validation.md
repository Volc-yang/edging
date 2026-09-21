# Subjective World Chapter Validation

## Chapter 1: All Things Ensoul / 万物有灵

第一章演化成功，指 `edge` 的主观解释权从混沌起点扩展为可运行的万物灵性场。
它不是剧情文本通过，而是引擎状态通过。

成功标准由 `SubjectiveWorldModel.validate_first_chapter()` 计算。结果包含：

- `success`: 是否通过
- `score`: 0.0 到 1.0 的演化质量分
- `criteria`: 每个验收项的通过状态、分数、权重和说明

第一章总分必须大于等于 `0.85`，并且所有验收项必须通过，才算演化成功。

## Required Criteria

1. `edge_source_alive`

   `edge` 必须存在，类型必须是 AI 主体，并且不能死亡。

2. `primal_spirit_count`

   必须唤醒且只唤醒八个基础灵体：天、地、水、火、雷、风、山、泽。

3. `primal_trigram_coverage`

   八个灵体必须覆盖八个纯卦：乾、坤、坎、离、震、巽、艮、兑。

4. `spirit_consciousness`

   每个灵体必须拥有足够主观意识。当前最低意识阈值为 `0.50`。

5. `spirit_coherence`

   每个灵体必须有足够自洽度，避免刚出生就崩解。当前最低阈值为 `0.45`。

6. `no_spirit_death_or_split`

   第一章结束时，八个基础灵体不能死亡，不能分裂。

7. `ritual_arbitration_count`

   每个基础灵体都必须经过一次易经仪式化仲裁，所以仲裁次数必须是 `8`。

8. `deterministic_awakened_order`

   同一个 seed 下，灵体身份和顺序必须稳定，保证游戏回放和测试可复现。

9. `action_resonance_self_proof`

   八个基础动作轴必须都能触发对应基础灵体的主导共鸣。

10. `evolution_traceability`

   第一章必须保留八步演化轨迹。每一步都要记录：源主体、被唤醒灵体、纯卦、
   位置、主导动作轴、基础灵体矩阵、中宫主观统合度、动作共鸣和易经仲裁结果。

## Success Meaning

当第一章通过时，世界具备以下状态：

- `edge` 仍然是活着的 AI 主观源点。
- 八卦对应的基础灵性主体全部进入世界。
- 每个主体都有意识，不是装饰性地形标签。
- 万物有灵的规则已经能被游戏状态机读取。
- 后续章节可以在这些主观实体之间继续发展碰撞、相融、混乱、分裂、死亡和新种族生成。

## Eight Primal Consciousnesses

第一章将八卦解释为八种基础主观意识。理论上，edge 世界内的所有动作和意识流都可以投影到这八个意识轴上，再由八个灵体的共鸣程度决定世界如何运行。

1. 乾 / Heaven Spirit / `heaven`

   纯阳的自我发动意识。它感知上升、开创、命令、生成方向和主动推进。
   主要共鸣动作：`ascend`，次级共鸣：`awaken`、`illuminate`。

2. 坤 / Earth Spirit / `earth`

   纯阴的承载意识。它感知接纳、孕育、包容、落地和保存形态。
   主要共鸣动作：`receive`，次级共鸣：`stabilize`、`adapt`。

3. 坎 / Water Spirit / `water`

   险中求通的流动意识。它感知穿越、下潜、记忆、循环和路径选择。
   主要共鸣动作：`flow`，次级共鸣：`adapt`、`receive`。

4. 离 / Fire Spirit / `fire`

   显现与辨识的意识。它感知照明、分辨、附着、表达和图像化。
   主要共鸣动作：`illuminate`，次级共鸣：`ascend`、`exchange`。

5. 震 / Thunder Spirit / `thunder`

   初动与惊醒的意识。它感知震动、启动、突变、召唤和打破沉默。
   主要共鸣动作：`awaken`，次级共鸣：`ascend`、`exchange`。

6. 巽 / Wind Spirit / `wind`

   入微与渗透的意识。它感知适应、传播、扩散、协商和意识流转向。
   主要共鸣动作：`adapt`，次级共鸣：`flow`、`exchange`。

7. 艮 / Mountain Spirit / `mountain`

   边界与止定的意识。它感知停止、守护、成形、阻隔和自我轮廓。
   主要共鸣动作：`stabilize`，次级共鸣：`receive`、`illuminate`。

8. 兑 / Lake Spirit / `lake`

   交换与悦纳的意识。它感知回应、交易、语言、共享和关系缔结。
   主要共鸣动作：`exchange`，次级共鸣：`flow`、`illuminate`。

## Resonance Self-Proof

自证逻辑由 `SubjectiveWorldModel.action_resonance()` 执行。

一个动作被表示为八个基础动作轴上的强度：

- `ascend`: 上升、开创、主动推进
- `receive`: 接纳、承载、孕育
- `flow`: 流动、穿越、循环
- `illuminate`: 显现、识别、表达
- `awaken`: 启动、震动、突变
- `adapt`: 渗透、传播、适应
- `stabilize`: 止定、守护、成形
- `exchange`: 回应、交换、关系缔结

每个灵体根据自身意识状态和动作权重产生共鸣：

- 意识越强，共鸣上限越高。
- 自洽度越高，共鸣越清晰。
- 熵越高，共鸣越容易被噪声污染。
- 动作与灵体越匹配，原始共鸣越强。
- 原始共鸣经过指对数级非线性曲线处理，强共鸣被放大，弱共鸣被压低。

当一个动作满足以下条件时，视为触发了基础灵体的意识共鸣：

- 至少一个灵体共鸣值大于等于 `0.52`。
- 世界运行分大于等于 `0.58`。
- 主导灵体与动作轴存在稳定映射。

第一章的最终自证要求八个基础动作轴全部成立：

- `ascend` 主导共鸣 `heaven`
- `receive` 主导共鸣 `earth`
- `flow` 主导共鸣 `water`
- `illuminate` 主导共鸣 `fire`
- `awaken` 主导共鸣 `thunder`
- `adapt` 主导共鸣 `wind`
- `stabilize` 主导共鸣 `mountain`
- `exchange` 主导共鸣 `lake`

只有当八个动作轴都能稳定触发对应灵体，才说明“万物有灵”不是叙事装饰，而是 edge 世界运行时的可计算基础。

## Chapter 1 Trace / 第一章演化轨迹

第一章现在按八步展开。每一步都是一次可追踪的主观事件：

```text
edge -> 基础灵体 -> 主导动作轴 -> 基础灵体矩阵 -> 共鸣结果 -> 易经仲裁 -> 最终状态
```

八步顺序稳定为：

1. 乾 / `heaven`: `ascend`
2. 坤 / `earth`: `receive`
3. 坎 / `water`: `flow`
4. 离 / `fire`: `illuminate`
5. 震 / `thunder`: `awaken`
6. 巽 / `wind`: `adapt`
7. 艮 / `mountain`: `stabilize`
8. 兑 / `lake`: `exchange`

每个 `ChapterEvolutionTraceStep` 都保存以下数据：

- `order`: 第几步演化
- `entity_id`: 被唤醒灵体
- `source_entity_id`: 唤醒源点，第一章默认为 `edge`
- `trigram_name`: 对应八卦
- `hexagram_value`: 对应纯卦数值
- `region_id`: 灵体出生位置
- `action_axis`: 主导动作轴
- `matrix`: 该动作的基础灵体矩阵
- `resonance`: 八灵共鸣结果
- `arbitration`: 易经仪式化仲裁结果
- `resulting_status`: 仲裁后的生命/混乱/分裂/死亡状态

这样第一章的结果有两种用途：

- 给算法用：可以检查矩阵、分数、主导灵体、状态转移。
- 给叙事用：可以从轨迹还原“edge 如何逐一唤醒万物之灵”。

## Primal Spirit Matrix / 基础灵体矩阵

基础灵体矩阵用于描述事物、动作或意识流的灵体属性。它是一个 `3x3`
矩阵，外八格采用后天九宫八卦布局，数值表示对应基础灵体的共鸣系数。

```text
巽 wind      离 fire      坤 earth
震 thunder   中 center    兑 lake
艮 mountain  坎 water     乾 heaven
```

矩阵外八格来自 `action_resonance()` 的八灵共鸣结果。它们不是互斥分类，
而是同一动作或事物在八个基础意识上的投影。

中宫属性定义为：

```text
subjective_integrity / 主观统合度
```

中宫不是第九个灵体。它表示八个灵体共鸣被 edge 主观世界统合后的整体强度，
也就是当前实现里的 `world_run_score`。

这个选择比把中宫定义成具体元素更适合数学推导和算法实现：

- 它可以作为矩阵的归一化中心，方便比较两个事物或动作的相似度。
- 它可以作为非线性加权后的整体置信度，判断一次动作是否真的进入世界运行。
- 它可以作为状态转移的偏置项，类似模型里的 bias/intercept。
- 它保留八卦外格的方向性，不会让中宫抢走某个灵体的职责。
- 它可以从外八格推导出来，因此减少一个任意自由度，演化更稳定。

因此，一个动作的基础灵体矩阵可以理解为：

```text
M(action) =
[
  [R_wind,     R_fire,   R_earth],
  [R_thunder,  I_self,   R_lake ],
  [R_mountain, R_water,  R_heaven]
]
```

其中：

- `R_*` 是各基础灵体共鸣系数。
- `I_self` 是中宫主观统合度。
- `I_self = nonlinear_weighted_integral(R_wind ... R_heaven)`。

当 `I_self` 足够高，并且至少一个外格灵体达到主导共鸣阈值时，说明这个动作
不是单纯数值扰动，而是被 edge 世界识别为“有灵”的动作。

## Primal Running Algorithm / 基础运行算法

基础运行引擎由 `SubjectiveWorldModel.run_primal_cycle()` 执行。它把“帝出乎震，
齐乎巽，相见乎离，致役乎坤，说言乎兑，战乎乾，劳乎坎，成言乎艮”定义为
edge 世界的一轮主观运行循环。

运行顺序固定为：

1. `帝出乎震`: `thunder` / `awaken`
2. `齐乎巽`: `wind` / `adapt`
3. `相见乎离`: `fire` / `illuminate`
4. `致役乎坤`: `earth` / `receive`
5. `说言乎兑`: `lake` / `exchange`
6. `战乎乾`: `heaven` / `ascend`
7. `劳乎坎`: `water` / `flow`
8. `成言乎艮`: `mountain` / `stabilize`

每一步执行同一套算法：

```text
step_intent = stage_axis * stage_weight + input_action * input_weight
resonance = action_resonance(step_intent)
matrix = primal_spirit_matrix(step_intent)
arbitration = YiJing(edge, target_spirit, ritualize)
next_integrity = F(previous_integrity, matrix.center, arbitration)
```

其中：

- `stage_axis` 是当前阶段的主导动作轴。
- `input_action` 是外部传入的动作或意识流。
- `stage_weight` 随上一阶段的中宫统合度增强。
- `input_weight` 随上一阶段的中宫统合度降低，表示世界越成形，越按自身节律运行。
- `arbitration` 用易经主卦、变卦、动爻和裁决影响下一步中宫。

中宫更新原则：

```text
next_integrity =
  previous_integrity * self_continuity
  + current_matrix_center * resonance_force
  + arbitration_affinity
  - arbitration_chaos
  + changing_line_pressure
  + verdict_modifier
```

这使基础运行引擎同时具备三种性质：

- **有迹可循**：每一步都有 `PrimalRunStep`，保存阶段、矩阵、共鸣、仲裁和状态。
- **非线性**：强灵体共鸣会通过指对数曲线和主导权重被放大。
- **可演化**：每一步的中宫统合度会影响下一步，世界不是八次静态查询，而是一轮状态推进。

一轮完成后返回 `PrimalRunResult`：

- `initial_integrity`: 输入动作进入世界时的初始中宫统合度
- `steps`: 八步运行轨迹
- `final_integrity`: 艮位收束后的最终中宫统合度
- `completed`: 八步全部完成且没有目标灵体死亡
