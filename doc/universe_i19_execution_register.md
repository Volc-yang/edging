# I19：只读 Metal 切片

2026-11-09；**in progress，UE未派发**；基线3a15f59，方案7eb3e9f。[方案树](design/universe-i19-metal-readonly-plan.md)。I18有限Native pass保留；父G-B2/完整矩阵仍open。

| 节点 | owner / worktree / branch / base | 当前事实 |
| --- | --- | --- |
| 0 | root + input/runtime只读规划 + independent review | C及显式v2切片方案审定pass，两个只读提案已反馈；P/R/M未运行 |
| C | i19_runtime_plan；`.worktrees/i19-metal-controller` / `codex/i19-metal-controller` /7eb3e9f | complete工具交付；PR125/head453fa9c→merge37a46ed，独立24+6CPU通过，最终CI42584966514 success；不表示实机pass |
| P | i19_input_plan；`.worktrees/i19-readonly-slice` / `codex/i19-readonly-slice` /9162000 | complete工具交付；PR126/head7b5349e→merge8c3523d，独立33CPU通过，最终CI42586193156 success；v2为14逻辑/1PNG/3请求，不授完整矩阵 |
| C2 | i19_runtime_plan；`.worktrees/i19-slice-admission` / `codex/i19-slice-admission` /8c3523d | complete工具交付；PR127/head7c37e3b→mergeef3d44d，独立40CPU通过，最终CI42587829711 success；固定新卡/manifest及完整计时 |
| R/M/X/T/A | root唯一运行 / independent review | root执行原件经独立审查修正后冻结中；未build/UE/worker/solver，无新Native/PNG/输入证据 |

CUA预检仅Finder现有输入框开/取消，已恢复。inventory首次30s timeout，第二次30.1830s成功；Finder绑定wall0.7606s（JS753ms），打开Go框+AX wall12.9134s（JS822ms），取消+AX wall4.3203s（JS1189ms）。内部时间不能替代完整往返；该记录是工具结果转录，非新UE性能证据。Codex app的getApp被工具策略拒绝后未重试该目标；不存在绕过界面权限的替代调用。

下一依赖：新prepared/card/固定driver精确SHA和独立ready复核，全部权限在clock前；不静默放宽v1/48call。只读抽象既有世界，不新Genesis solve；用户主checkout/I12B/I15构建/旧goal/DNS/API不动。

固定运行原件：[prepare](evidence/universe-I19R/prepare.py)、[driver](evidence/universe-I19R/driver.py)。同一driver读取本会话未来且带I19STEP标识的实际CUA call/output两行原字节，不复制历史对话或其他工具；[真实schema预检](evidence/universe-I19R/raw-cua-preflight-check.json)已由同一parser独立复核。新Native仅本轮两响应；Native normal/evidence_frozen与resource均实际核对后才置finished。原生PNG沿现有capture API，早期log ref仅在退出/稳定封存后发布；全root使用nofollow遍历并记录异常。startup可做I19BIND窗口绑定/聚焦/全屏，物理操作及时间单独保存并计入startup60/Metal420/global900，不冒充业务逻辑命令。
