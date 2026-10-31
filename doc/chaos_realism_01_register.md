# CHAOS-REALISM-01 任务登记

统筹 worktree `.worktrees/chaos-realism-01`；分支 `codex/chaos-realism-01`；基线 `6697512`。DevSSD 专用输出根 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/`。任务卡见 `doc/chaos_realism_01_plan.md`。

| ID | Owner / 状态 | worktree / 分支 / 基线 | 交付 | PR / 测试 / 清理 |
| --- | --- | --- | --- | --- |
| P1 | `/root/chaos_realism_p1`；完成 | `.worktrees/chaos-realism-p1` / `codex/chaos-realism-p1` / `72b25d8` | 插件、资产来源与接口提案；无写实外部资产 | PR #13，`36f8590`，合并 `564ce35`；CI 通过，干净 worktree 已移除 |
| T1 | `/root/chaos_realism_t1`；代码完成、视觉未过 | `.worktrees/chaos-realism-t1` / `codex/chaos-realism-t1` / `564ce35` | 程序地形/水面、地表采样；UE 构建/NullRHI/Metal 日志通过，DevSSD PNG 黑屏 | PR #15，`42de326`，合并 `e2a08f0`；仅本轮自动生成 Build/DefaultInput 清除后干净 worktree 已移除 |
| E1 | `/root/chaos_realism_e1`；代码完成、视觉未验 | `.worktrees/chaos-realism-e1` / `codex/chaos-realism-e1` / `e2a08f0` | 确定性 HISM 生态代理；UE Editor/Game、NullRHI 与 CI 通过 | PR #16，`40db79b`，合并 `f1c0516`；干净 worktree 已移除 |
| L1 | `/root/chaos_realism_l1`；代码完成、未组装 | `.worktrees/chaos-realism-l1` / `codex/chaos-realism-l1` / `564ce35` | 日间光照；UE Editor/Game 构建通过，无 Metal 场景 | PR #14，`35c35ab`，合并 `18b1b6b`；干净 worktree 已移除 |
| V1 | `/root/chaos_realism_v1`；部分完成，视觉门失败 | `.worktrees/chaos-realism-v1` / `codex/chaos-realism-v1` / `95601b6` | Metal 非黑屏；tick 0/1 只读隔离通过；地表/水体蓝色、植被仍为代理；帧时间未测。原始图/日志在 DevSSD `Renders/V1`、`Logs/V1` | PR #17，`7dd9736`，合并 `ac80172`；干净 worktree 已移除 |
| T1-VF | `/root/chaos_realism_t1`；代码完成，独立组装复测待 V2 | `.worktrees/chaos-realism-t1-visual-fix` / `codex/chaos-realism-t1-visual-fix` / `7ad6c2a` | 翻转 `FSection::Quad` 绕序；独立 Metal 预览已显示绿色地形、米色海岸、蓝色水体和棕色路线；不改 Worker | PR #18，`734bbdf`，合并 `93ee1a7`；UE Editor build/CI 通过，DevSSD `Renders/Terrain` 有预览与日志；干净 worktree 已移除 |
| V2 | `/root/chaos_realism_v1`；技术视觉链路通过，写实/性能门开放 | `.worktrees/chaos-realism-v2` / `codex/chaos-realism-v2` / `93ee1a7` | 组装场景森林/河泽/海岸/路线 Metal 可辨；tick 0/1 相机和 observe 前后权威 manifest/state/event 不变，显式 O1 才推进；实际帧时间未测 | PR #19，`6a84b3b`，合并 `3c8de2f`；CI 通过，干净 worktree 已移除；原图/日志在 DevSSD `Renders/V2`、`Logs/V2` |
| A1 | 主任务；本轮技术纵切收尾 | 统筹 worktree | `95601b6` 连接 Worker 观察、T1/E1/L1；V1 发现并经 T1-VF/V2 修复地表剔除 | UE Editor 构建、Metal 技术画面与只读隔离通过；写实美术与帧时间门开放，未合入 `feature/edge-world` |

当前已有用户交互启动的 UE Chaos 进程；P1 只读调查不会终止它。后续实际运行验收先检查进程和状态目录，避免两个 Worker 共用存档。

V1 蓝色画面不是成功的水体效果：程序地形、水面和路线的三角形绕序与顶视正面方向冲突，单面被剔除；树木代理因此像悬浮。T1-VF 翻转绕序后的独立 Metal 预览验证了该诊断，组装场景仍待 V2 复测。当前缺乏授权写实资产，修复几何可见性仍不等于写实美术达标。
