# CHAOS-REALISM-01 任务登记

统筹 worktree `.worktrees/chaos-realism-01`；分支 `codex/chaos-realism-01`；基线 `6697512`。DevSSD 专用输出根 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/`。任务卡见 `doc/chaos_realism_01_plan.md`。

| ID | Owner / 状态 | worktree / 分支 / 基线 | 交付 | PR / 测试 / 清理 |
| --- | --- | --- | --- | --- |
| P1 | `/root/chaos_realism_p1`；执行中 | `.worktrees/chaos-realism-p1` / `codex/chaos-realism-p1` / `72b25d8` | 插件、资产来源与接口可行性 | 待反馈，保留 worktree |
| T1 | 待 P1 | 待建 | 地形与水体样区 | 待执行 |
| E1 | 待 T1 | 待建 | 生态呈现 | 待执行 |
| L1 | 待 P1 | 待建 | 材质与天空 | 待执行 |
| V1 | 待 T1/E1/L1 | 待建 | Metal 独立证据 | 待执行 |
| A1 | 主任务 | 统筹 worktree | 审查集成与上下文 | 进行中 |

当前已有用户交互启动的 UE Chaos 进程；P1 只读调查不会终止它。后续实际运行验收先检查进程和状态目录，避免两个 Worker 共用存档。
