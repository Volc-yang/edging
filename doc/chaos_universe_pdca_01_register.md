# PDCA-CHAOS-01 工作树与任务登记

状态：进行中。用户于 2026-10-27 明确要求执行已提交的 PDCA 任务卡并分配 subagents；此授权视为方案树实现审阅通过。详细任务边界见 `doc/chaos_universe_pdca_01_subplans.md`。

仓库：`/Users/yangacan/edgeWorld/edge-world`。统筹/集成 worktree：`.worktrees/chaos-universe-pdca-plan`，分支 `codex/chaos-universe-pdca-plan`，派工前 HEAD `8f5ca98`。主工作区 `feature/edge-world` 含用户未提交内容；既有 Seed→Tree PIE worktree 仍进行中。两者不作为本轮写入位置。

| ID | 负责人 / 状态 | worktree / 分支 / 基线 | 所有权 | 依赖与交付 | PR / 测试移交 / 清理 |
| --- | --- | --- | --- | --- | --- |
| P0 | `/root/chaos_p0`；完成，已审查集成 | `.worktrees/chaos-p0` / `codex/chaos-p0` / `8f5ca98` | `doc/chaos_origin_contract.md` | 提交 `3713991`；初态/state/event 固定摘要由统筹独立复算一致 | PR #1 已合并为 `2659242`，CI verify 成功；干净工作树已移除，本地任务分支已删除 |
| D1 | `/root/chaos_d1`；完成，已审查集成 | `.worktrees/chaos-d1` / `codex/chaos-d1` / `10ff215` | 新 `engine/chaos/world_generation.py`、`initial_state.py`、示例 manifest、定向测试 | 提交 `b0c97f6`；seed 7 与 P0 SHA-256 一致，6 项定向检查通过；其他 seed 只改潜势 | PR #2 已合并为 `3e7a8c2`，CI verify 成功；干净工作树已移除，本地任务分支已删除 |
| D2 | `/root/chaos_d2`；完成，已审查集成 | `.worktrees/chaos-d2` / `codex/chaos-d2` / `10ff215` | 新 `origin_runtime.py`、`origin_store.py`、`origin_worker.py`、定向测试 | 提交 `2b7fc3d`、修复 `0397030`；复用 D1 完整地理校验，临时文件失败正确归类；8 项定向检查与真实 D1 JSON 通过 | PR #3 已合并为 `f7eaef8`，CI verify 成功；干净工作树已移除，本地任务分支已删除 |
| D3 | `/root/chaos_d3`；静态场景任务完成，已审查集成 | `.worktrees/chaos-d3` / `codex/chaos-d3` / `10ff215` | 新 UE `ChaosWorld*`、`ChaosGameMode*` 源码与专用说明 | 提交 `cbbf8d2`；UE 5.8.3 Editor build、NullRHI 六类场所启动与 fixture 摘要核对通过；BasicShapes 代理、真实 RHI/美术质量未验证 | PR #4 已合并为 `0fe0a82`，CI verify 成功；干净工作树已移除，本地任务分支已删除 |
| D4 | `/root/chaos_d4`；实现完成、真实画面待 C2 | `.worktrees/chaos-d4` / `codex/chaos-d4` / `5dc6b6a` | 新 UE `ChaosObservation*`，核准范围内的 `EdgeWorldJsonlClient.h/.cpp` | PR #6、`7d9afcd`、合并 `2bbc3aa`；UE Editor 构建、NullRHI 协议、14 项 Python 与 CI 通过；真实 RHI 未验 | 干净工作树已移除，本地分支已删除 |
| C1 | `/root/chaos_c1`；完成 | `.worktrees/chaos-c1` / `codex/chaos-c1` / `5dc6b6a` | `doc/evidence/chaos-pdca-01/state-review.md` | PR #5、`b5da0a5`、合并 `34dec83`；14 项定向测试及 CI 通过，有限单进程 Python 状态门通过 | 干净工作树已移除，本地分支已删除 |
| C2 | `/root/chaos_c2`；部分完成 | `.worktrees/chaos-c2` / `codex/chaos-c2` / `2bbc3aa` | `doc/evidence/chaos-pdca-01/visual-review.md` | PR #7、`d89fef2` + `98f85ec`、合并 `72e52da`；Metal tick 0/1 与显式 O1、有限只读通过；相机/帧率/UE 暂停、六类连贯性及视觉质量未验；CI 通过 | 干净工作树已移除，本地分支已删除 |
| A1 | 主任务；待执行 | 集成 worktree | 本登记、统筹清单、集成决策 | PDCA 复盘及下一轮入口 | 待执行 |

接口裁决：D2 的 chaos worker 从 `--initial-world` 读取 D1 JSON，并兼容现有 UE 进程启动器的 `--dt/--physical-steps/--seed`；D4 可对 `EdgeWorldJsonlClient.h/.cpp` 增加可选初态路径和 O1 专用请求，必须保持既有树/Genesis 请求不变并有回归证据。D1/D2 无共享 Python 源码所有权。

下一动作：A1 已复盘；下一轮先提供可自动驱动的 UE 测试入口，以固定相机、帧率、UE Pause/Resume 和显隐做逐项状态摘要对照，再逐区采图核查六类场所与路线。D4 的 canonical hash 核验限 macOS；D3/D4 对初态文件分开读取，本轮 C2 用只读固定输入但未消除竞态。P0 的居民/玩家身份自然触发机制仍是明确开放的世界观问题，不阻塞本轮显式 O1 技术纵切。
