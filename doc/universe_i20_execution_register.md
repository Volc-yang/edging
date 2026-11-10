# I20：新写实需求的首轮PDCA

2026-11-10；**complete：仅A/B/C源输入、设计/CPU契约及父级集成门**。输入e76f4b6；[独立审定方案树](design/universe-i20-realistic-pdca-plan.md)保持原字节，parent为[Dot需求接入](design/edge-dot-realistic-rendering-intake-20261110.md)。D0延期，D3代码/UE编译和D4实拍是后续轮次；写实产品目标仍未验收。[统筹结算](evidence/universe-I20R/report.md)。

| 节点 | owner / branch / path | 状态与实际结果 |
| --- | --- | --- |
| P0 | root；codex/plan-consolidation | complete；两个只读subagents完成平台/Universe调查，独立review接受方案及两项执行澄清 |
| D0 | root；交付询问 | deferred；用户已授权询问Dot，但可用消息API/聊天清单无可寻址Dot/Edge，尚未发送；[待交接请求](evidence/universe-I20R/dot-delivery-request.md)；不是等待额外授权，不阻塞本轮ABC |
| A | i20_assets_plan；codex/i20-assets / .worktrees/i20-assets | complete源输入；PR128/head30907e8→mergea3ca6a4，CI42753910052 success；实际20payload/41,949,796B，完整响应体42,116,535B/145.219s，34files；owner与独立源/依赖/解码及root稳定路径检查通过；无UE导入 |
| B | i20_universe_plan；codex/i20-profile / .worktrees/i20-profile | complete设计/CPU；PR129/headd6fe60d→merge0dfde3e，CI42754957084 success；15项owner/独立重跑+5项独立检查通过；1e999缺口定点返工，原失败保留；root稳定路径15项/exit0，未改旧authority/parser |
| C | root + i20_review；codex/i20-review / .worktrees/i20-review，基线6c533af | complete审查/集成；独立3627af2经root审读，按父任务证据交付直接-x摘取为6996d71（非另一个实现PR）；A/B/C共50个原件逐字节一致、34个持久文件/hash与所有审查收据通过；[parent check](evidence/universe-I20R/parent-check-01/integration-check.json) |

实际平台观察：UE5.8.3 CL58210709；当前xcode-select为Xcode.app，xcodebuild报告27.2/27B52；安装内SDK文件允许15.2.0–27.9.0，未运行本轮UE编译。主checkout用户改动、I15构建和I12B恢复树、旧失败与网站/DNS/API不改。无新goal、无UE/GPU/worker/Genesis运行。

清理：A/B/C三棵任务树干净、交付已集成且无运行依赖，经检查后non-force移除；分支、Git原件、DevSSD资产全留。A历史receipt中的旧helper路径由既有分阶段来源映射解析，不改旧记录。[前置检查](evidence/universe-I20R/worktree-cleanup-preconditions.json) / [实际清理](evidence/universe-I20R/worktree-cleanup.json)。统筹树保留；只合入codex/plan-consolidation，未同步feature/edge-world。

下轮第一入口：[D3-IMPORT / D3-ADAPTER / D3-BUILD / D4-LOOKDEV卡](design/universe-realistic-presentation-profile.md#act可独立执行的后续d3d4任务卡)。先审定新执行树和导入/编译预算，固定A源index d9df98db…447b7及真实UE producer；D3-IMPORT提供实际package/class/slots/units/pivot/bounds/材质后，D3-ADAPTER实现profile与HUD/场景同次提交，再准确源码编译；D4另卡验收Metal原PNG、只读、正常退出及画质/性能。卡已落盘，**尚未派发或运行**；不以合成profile替代真实Native输入。I18 exact3接受和I19stdin失败保持原状。
