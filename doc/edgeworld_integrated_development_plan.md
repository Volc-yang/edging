# edgeWorld 4D 数字宇宙：集成开发总图

状态：2026-11-01，v0.3。当前计划入口；历史任务的原始裁决和证据仍以各任务登记及报告为准。远端基线 `feature/edge-world` 的 PR #25 合并提交为 `383c72e`；后续有限 Seed→Tree × Genesis 纵切在集成分支 `codex/plan-consolidation`，未因此自动进入基线。

当前进展：抽象 Seed→Tree × Genesis 已有有限真实 Metal 集成证据；H6B 可步行实现经 PR #66 集成，H6C 独立访问、两模式推进、历史只读与恢复有限门经 PR #69 接受并集成（`0344827`）。显式 `--viewport-preflush` 开发入口有限接受；默认关闭路径可靠性、reporter 自身退出、正式视觉/性能门仍开放，V-HOME 未接受。准确提交和原始证据见[统筹清单](parallel_execution_backlog.md)。

**下一阶段设计入口：[AI 4D 数字宇宙架构设计树](universe_architecture_design_plan.md)**。设计从世界身份/因果与丰富混沌初态两条路径开始，覆盖 Genesis、AI 提案、事务恢复、载具访问、UE 时间投影、写实与规模预算。它是设计计划，未将开放世界法则或数值阈值升级为批准决定。
## G：产品目标与架构边界

目标是建立可由 AI 参与生成、由人类通过载具登陆、游玩和重访的持久 4D 数字宇宙。4D 的技术含义是权威世界状态在逻辑时间中演化，观察者可从指定时间和位置取得呈现。玩法、物理法则、植物演化规则与视觉标准须由各自产品/技术契约批准；PDCA 只控制开发过程。

- 4D 状态、事件、逻辑时间与恢复由权威层负责；UE 相机、帧率、Actor 生命周期和只读查询不得隐式推进状态。AI 输出先是提案，不能直接提交世界状态。
- 优先使用 UE5 发布版渲染、插件和适配层连接 Genesis 与权威层。仅当已批准契约出现可复现缺口，且插件/适配替代方案失败时，才另立源码改动评估卡。
- 单树、单刚体和六类场所的现有原型都是有限纵切；它们不代表生产规模、完整世界法则或最终写实质量。

## 旧计划与当前 PDCA 的关系

| 历史计划/成果 | 当前节点 | 使用方式 |
| --- | --- | --- |
| [4D 引擎执行计划](edgeworld_4d_engine_execution_plan.md)阶段 0–2、[阶段 1 实验契约](phase1_4d_prototype_contract.md) | G0/G1、G2a/b/c、G3 | 保留原型边界和 UE↔worker↔Genesis 有限证据；阶段 3–6 映射为后续能力路线，不按旧估时直接开工 |
| [Seed→Tree 契约](seed_tree_4d_render_slice_contract.md)与 [backlog](parallel_execution_backlog.md) | G2a/c、G3/G4 | 确定性演化和 UE BasicShapes Standalone 作为技术基线；规则系数、PIE/完整观察矩阵继续开放 |
| [混沌第一轮](chaos_universe_pdca_01_plan.md)、[第二轮](chaos_universe_pdca_02_plan.md) | G2a/c、G3/G4 | 六类初态、CHAOS→ONE、Metal 代理可辨和控制只读证据可复用；TWO 尚未启动 |
| [写实样区](chaos_realism_01_plan.md) | G2c、G3/G4 | 森林—河泽—海岸 Metal 技术呈现及输入修复可复用；美术和实测性能继续开放 |
| [递归 PDCA 总计划](ai_4d_universe_pdca_master_plan.md)、[G0 提案](pdca_g0_version_goal_proposal.md) | G、G0–G5、GQ | 作为过程和任务卡结构；G0 过程规划门已由用户接受，提案第 4 节运行阈值尚待冻结 |

## 证据与验收状态

| 能力 | 已有结果 | 尚未通过的门 |
| --- | --- | --- |
| UE↔worker↔Genesis 阶段 2 | 有单刚体、显式推进、观察与恢复的有限纵切；见 [backlog](parallel_execution_backlog.md) | 生产级物理、规模及跨平台 |
| Seed→Tree | Worker 重演/幂等/恢复及 UE Standalone Metal 成树画面有记录 | 生长规则批准、PIE 完整只读矩阵、产品级植被 |
| CHAOS→ONE | 固定 seed7 初态、六类 BasicShapes 代理及路线可辨；相机/暂停/显隐/历史观察的已执行只读检查通过；见[第二轮登记](chaos_universe_pdca_02_register.md) | TWO、最终世界美术、跨平台和生产并发；FPS 设定回读不等于帧时间实测 |
| 写实样区 | V1 视觉失败后 T1-VF 修复，V2 Metal 复测技术呈现通过，权威状态隔离通过；见[登记](chaos_realism_01_register.md) | 仍为程序代理；授权写实资产、视觉标准和 CPU/GPU trace 未通过 |
| 开发框架 | F0/F1/F2 集成，G0 过程规划门接受；见[总计划](ai_4d_universe_pdca_master_plan.md)与[登记](ai_4d_universe_pdca_register.md) | G0 产品阈值、目标机器/规模/预算冻结；GQ 正式性能门及产品端到端门尚无通过证据；已有 GQ 有限信号试采 |
| 可访问因果观测场景 | V-HOME H2/H3 场景与 HUD、H4 准确组合提交的 UE Metal tick 0/1/2、只读历史和重启有[有限证据](evidence/home-integration/report.md)；GQ 导出 600 帧 CPU/GPU 同窗信号 | H5 独立体验复核、间歇性 `SceneViewport` 退出断言、正式视觉/性能门；BasicShapes 场景不是写实世界 |

历史失败不因后续修复而抹去；每次 Check 绑定构建、输入、配置、阈值版本和原始证据。PR 合并、子任务完成、父级集成通过和产品验收是不同状态。

## 拓扑与下一批任务卡

```text
G0 过程规划接受 ─┬─ G1 接口与版本范围 ─┬─ G2a 4D 状态/演化 ─┐
                │                     ├─ G2b Genesis 物理 ──┤
                │                     ├─ G2c UE 呈现/输入 ──┼─ G3 纵切集成 ─ G4 独立验收 ─ G5 复盘/发布
                │                     └─ G2d AI 提案 ───────┘
                └─ GQ 证据/性能基准 ────────────────────────┘
G0 产品门阈值冻结 ────────────────→ 受影响的 G2 实施与 G4 判定
```

旧 G1/GQ 规划卡已在历史轮次形成接口提案、负例探针与信号试采，不再作为“尚未开始”的任务重复派发。G0 未决产品规律和正式阈值仍由[决策记录](pdca_g0_freeze_decision_record.md)维护；技术 fixture 的有限放行不替代产品冻结。

U1 世界身份/因果与 U5 丰富混沌初态已完成独立设计 PR 和局部集成审查，见[首批结果](design/universe-u1-u5-integration-review.md)。U2/U3/U6/U7 第二批也已交付并通过局部设计门，见[第二批审查](design/universe-batch2-integration-review.md)。U4 事务/调度/恢复设计经 PR #74 接受（仅设计门），见[复核](design/universe-u4-integration-review.md)。U8 规模/质量预算设计经 PR #75 接受（候选数值不升级为产品门），见[复核](design/universe-u8-integration-review.md)。下一 ready 为 U9 最终跨卡审查与实现树，尚未派发；H6C 独立运行及审查已完成，有限门接受，不转移为写实世界产品验收。AI、载具登陆、完整物理、TWO 和最终写实世界目前没有可宣称通过的产品门。

## 仓库与历史边界

PR #25 已将既有规划及纵切分支合入远端 `feature/edge-world`（`383c72e`）。本地主工作区仍在旧提交并有用户未提交/未跟踪内容；本计划的集成状态指远端基线，不意味着本地主工作区已同步。旧任务登记保留当时的分支和门状态作为历史记录。未找到此前 Google 元宇宙对比原文，不能据此补写结论。
