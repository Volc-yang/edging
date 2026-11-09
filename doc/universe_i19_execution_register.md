# I19：只读 Metal 切片

2026-11-09；**in progress，UE未派发**；基线3a15f59，方案7eb3e9f。[方案树](design/universe-i19-metal-readonly-plan.md)。I18有限Native pass保留；父G-B2/完整矩阵仍open。

| 节点 | owner / worktree / branch / base | 当前事实 |
| --- | --- | --- |
| 0 | root + input/runtime只读规划 + independent review | C-only审定pass，P/R/M未ready；两份只读提案均已反馈，无运行 |
| C | i19_runtime_plan；`.worktrees/i19-metal-controller` / `codex/i19-metal-controller` /7eb3e9f | 453fa9c待独立审查/PR/CI；13new+11legacy CPU、CLI6 owner检查pass，不表示实机pass |
| P | root + input planner | CUA已连通；真实完整往返超过旧2s，正在独立审查固定窄切片v2；未创建prepared/card或DevSSD运行目录 |
| R/M/X/T/A | root唯一运行 / independent review | pending；未build/UE/worker/solver，无新Native/PNG/输入证据 |

CUA预检仅Finder现有输入框开/取消，已恢复。inventory首次30s timeout，第二次30.1830s成功；Finder绑定wall0.7606s（JS753ms），打开Go框+AX wall12.9134s（JS822ms），取消+AX wall4.3203s（JS1189ms）。内部时间不能替代完整往返；该记录是工具结果转录，非新UE性能证据。Codex app的getApp被工具策略拒绝后未重试该目标；不存在绕过界面权限的替代调用。

下一依赖：C独立审查/最终CI；P显式版本化成本/范围审定后才创建写树，不静默放宽v1/48call。只读抽象既有世界，不新Genesis solve；用户主checkout/I12B/I15构建/旧goal/DNS/API不动。
