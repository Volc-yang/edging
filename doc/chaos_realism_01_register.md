# CHAOS-REALISM-01 任务登记

统筹 worktree `.worktrees/chaos-realism-01`；分支 `codex/chaos-realism-01`；基线 `6697512`。DevSSD 专用输出根 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/`。任务卡见 `doc/chaos_realism_01_plan.md`。

| ID | Owner / 状态 | worktree / 分支 / 基线 | 交付 | PR / 测试 / 清理 |
| --- | --- | --- | --- | --- |
| P1 | `/root/chaos_realism_p1`；完成 | `.worktrees/chaos-realism-p1` / `codex/chaos-realism-p1` / `72b25d8` | 插件、资产来源与接口提案；无写实外部资产 | PR #13，`36f8590`，合并 `564ce35`；CI 通过，干净 worktree 已移除 |
| T1 | `/root/chaos_realism_t1`；代码完成、视觉未过 | `.worktrees/chaos-realism-t1` / `codex/chaos-realism-t1` / `564ce35` | 程序地形/水面、地表采样；UE 构建/NullRHI/Metal 日志通过，DevSSD PNG 黑屏 | PR #15，`42de326`，合并 `e2a08f0`；仅本轮自动生成 Build/DefaultInput 清除后干净 worktree 已移除 |
| E1 | `/root/chaos_realism_e1`；代码完成、视觉未验 | `.worktrees/chaos-realism-e1` / `codex/chaos-realism-e1` / `e2a08f0` | 确定性 HISM 生态代理；UE Editor/Game、NullRHI 与 CI 通过 | PR #16，`40db79b`，合并 `f1c0516`；干净 worktree 已移除 |
| L1 | `/root/chaos_realism_l1`；代码完成、未组装 | `.worktrees/chaos-realism-l1` / `codex/chaos-realism-l1` / `564ce35` | 日间光照；UE Editor/Game 构建通过，无 Metal 场景 | PR #14，`35c35ab`，合并 `18b1b6b`；干净 worktree 已移除 |
| V1 | `/root/chaos_realism_v1`；执行中 | `.worktrees/chaos-realism-v1` / `codex/chaos-realism-v1` / `95601b6` | DevSSD Metal 独立画面/状态/帧时间证据 | 待反馈，保留 worktree |
| A1 | 主任务；组装完成、复盘待 V1 | 统筹 worktree | `95601b6` 连接 Worker 观察、T1/E1/L1；UE Editor 构建通过，Metal 待 V1 | 进行中 |

当前已有用户交互启动的 UE Chaos 进程；P1 只读调查不会终止它。后续实际运行验收先检查进程和状态目录，避免两个 Worker 共用存档。
