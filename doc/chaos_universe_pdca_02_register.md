# PDCA-CHAOS-02 任务登记

仓库 `/Users/yangacan/edgeWorld/edge-world`；统筹 worktree `.worktrees/chaos-pdca-02`，分支 `codex/chaos-pdca-02`，基线 `7cb65d2`。计划见 `doc/chaos_universe_pdca_02_plan.md`。

| ID | 负责人/状态 | worktree/分支/基线 | 交付与证据 | PR/集成/清理 |
| --- | --- | --- | --- | --- |
| H1 | `/root/chaos_h1`；实现完成、Metal 待 C3 | `.worktrees/chaos-h1` / `codex/chaos-h1` / `40567d7` | opt-in 控制入口；UE Editor/Game 构建、live NullRHI ack/O1、CI 通过 | PR #9，`9a78c58`，合并 `dffaccc`；干净工作树已移除 |
| V1 | `/root/chaos_v1`；实现完成，真实 Metal 待 C3 | `.worktrees/chaos-v1` / `codex/chaos-v1` / `40567d7` | 六类场所与路线代理；UE Editor 构建、fixture/seed7 NullRHI、CI 通过 | PR #8，`f556012`，合并 `52029e6`；干净工作树已移除 |
| C3 | `/root/chaos_c3`；执行中 | `.worktrees/chaos-c3` / `codex/chaos-c3` / `dffaccc` | Metal 独立完整矩阵报告 | 待反馈；保留工作树 |
| V1R | V1 原 owner 待重新启用 | 待建 | 修复 C3 截图证实的地形遮挡 | 待执行 |
| C4 | 待 V1R | 待建 | 独立复测六区与路线画面 | 待执行 |
| A2 | 主任务 | 统筹 worktree | 审查、集成、复盘和上下文提交 | 进行中 |

主工作区现有未提交改动及旧 PIE worktree 均不属于本轮。仅移除已合并且干净的本轮任务 worktree；原始大型画面证据在独立 Saved 目录保留。
