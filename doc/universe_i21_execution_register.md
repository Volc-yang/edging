# I21：真实UE资产导入

2026-11-10；**in progress；计划已审定**。固定输入基线d5ada8fcddf215f6fb4bcf9cabea65699ad8ae91，统筹树`.worktrees/plan-consolidation` / branch`codex/plan-consolidation`。[计划树](design/universe-i21-native-import-plan.md)的审定SHA为12e964370403c52b36e65ebe4a96f4dae3ee554b40fe1e6239a5ed7224dd9f97；[C0裁决](evidence/universe-I21R/plan-review.json)。实现树从本次冻结计划commit创建，另登记准确SHA。源payload在I20 DevSSD目录，未改主checkout；无新goal。

| 节点 | owner / branch / worktree | 状态 |
| --- | --- | --- |
| P0 | root + i20_assets_plan + i20_universe_plan | complete；两位旧agent只读调查发布版导入API和呈现交接边界 |
| C0 | i20_review | accepted；最终12e96437方案，准许冻结和派发A；准确代码/argv仍须C1接受后才运行UE |
| A | 待审定后派发 | queued；脚本/recipe/CPU边界检查；真实UE由root执行 |
| R | root | not dispatched；最多2 import+1 reload/900s/4GiB，NoTrace/独占DDC、无可见窗口 |
| C2 | 独立reviewer | queued；核实际原件，parent root随后集成与清理 |

本轮目标为真实导入和新进程回读，不运行Universe/worker/Genesis、不改GameMode，不宣称实际画质。D3-ADAPTER/准确C++构建与D4 Metal实拍依赖本轮真实metadata。I18/I19/I20裁决及未知Dot候选状态保持。
