# PDCA-CHAOS-01 工作树与任务登记

状态：进行中。用户于 2026-10-27 明确要求执行已提交的 PDCA 任务卡并分配 subagents；此授权视为方案树实现审阅通过。详细任务边界见 `doc/chaos_universe_pdca_01_subplans.md`。

仓库：`/Users/yangacan/edgeWorld/edge-world`。统筹/集成 worktree：`.worktrees/chaos-universe-pdca-plan`，分支 `codex/chaos-universe-pdca-plan`，派工前 HEAD `8f5ca98`。主工作区 `feature/edge-world` 含用户未提交内容；既有 Seed→Tree PIE worktree 仍进行中。两者不作为本轮写入位置。

| ID | 负责人 / 状态 | worktree / 分支 / 基线 | 所有权 | 依赖与交付 | PR / 测试移交 / 清理 |
| --- | --- | --- | --- | --- | --- |
| P0 | `/root/chaos_p0`；完成，已审查集成 | `.worktrees/chaos-p0` / `codex/chaos-p0` / `8f5ca98` | `doc/chaos_origin_contract.md` | 提交 `3713991`；初态/state/event 固定摘要由统筹独立复算一致 | PR #1 已合并为 `2659242`，CI verify 成功；工作树待清理 |
| D1 | 待分配 | 待 P0 审查后固定 | 新 `engine/chaos/world_generation.py`、`initial_state.py`、示例 manifest、定向测试 | 世界初态与拓扑 | 待执行 |
| D2 | 待分配 | 待 P0 审查后固定 | 新 `origin_runtime.py`、`origin_store.py`、`origin_worker.py`、定向测试 | O1 权威提交与恢复 | 待执行 |
| D3 | 待分配 | 待 P0 审查后固定 | 新 UE `ChaosWorld*` 源码 | 六类场所静态呈现 | 待执行 |
| D4 | 待分配 | 待 D1+D2+D3 接口审查 | 新 UE `ChaosObservation*` 源码 | 固定状态观察接线 | 待执行 |
| C1 | 待分配 | 待 D1+D2 | `doc/evidence/chaos-pdca-01/state-review.md` | 因果/恢复独立核查 | 待执行 |
| C2 | 待分配 | 待 D4 | `doc/evidence/chaos-pdca-01/visual-review.md` | 真实画面/只读独立核查 | 待执行 |
| A1 | 主任务；待执行 | 集成 worktree | 本登记、统筹清单、集成决策 | PDCA 复盘及下一轮入口 | 待执行 |

下一动作：以已审查的 P0 契约与统筹上下文提交为共同固定基线，创建 D1/D2/D3 各自 worktree 并并行派工。P0 的居民/玩家身份自然触发机制仍是明确开放的世界观问题，不阻塞本轮显式 O1 技术纵切。
