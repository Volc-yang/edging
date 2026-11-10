# I20：新写实需求的首轮PDCA

2026-11-10；**in progress**。输入e76f4b6；[已独立审定方案树](design/universe-i20-realistic-pdca-plan.md)，parent为[Dot需求接入](design/edge-dot-realistic-rendering-intake-20261110.md)。本轮目标是取得可复现真实资产输入、冻结只读呈现契约/测试卡并审查，D3代码/UE编译和D4实拍另卡；不能将本轮完成写成3A画质通过。

| 节点 | owner / branch / path | 状态与实际结果 |
| --- | --- | --- |
| P0 | root；codex/plan-consolidation | complete；两个只读subagents完成平台/Universe调查，独立review接受方案及两项执行澄清 |
| D0 | root；交付询问 | pending；用户已明确授权询问Dot，但可用消息API/聊天清单无可寻址Dot/Edge，尚未发送；[待交接请求](evidence/universe-I20R/dot-delivery-request.md)；不是等待额外授权 |
| A | i20_assets_plan；codex/i20-assets / .worktrees/i20-assets | queued；实际CC0文件及许可证/依赖/摘要待取得；固定256MiB/64files/20min限额，无UE导入 |
| B | i20_universe_plan；codex/i20-profile / .worktrees/i20-profile | queued；profile/ViewBinding设计、schema/正负例与语义测试卡待交付；旧authority/parser不改 |
| C | root + i20_review；独立报告树待交付后建立 | queued；逐项原件、测试、差异与PR审查后集成；不以任务回报代替验证 |

实际平台观察：UE5.8.3 CL58210709；当前xcode-select为Xcode.app，xcodebuild报告27.2/27B52；安装内SDK文件允许15.2.0–27.9.0，未运行本轮UE编译。主checkout用户改动、I15构建和I12B恢复树、旧失败与网站/DNS/API不改。无新goal、无UE/GPU/worker/Genesis运行。

后续第一入口：A实际资源身份与B映射/事务接口交叉固定后，向D3发布准确源/素材/平台与负例卡，随后按新预算实机D4。I18 exact3接受和I19stdin失败保持原状。
