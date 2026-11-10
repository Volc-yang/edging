# I21：真实UE资产导入

2026-11-10；**partial；有界运行结算，Native导入门失败，草稿PR130已公开发布**。固定输入基线d5ada8fcddf215f6fb4bcf9cabea65699ad8ae91，冻结计划commit6eae279，统筹树`.worktrees/plan-consolidation` / branch`codex/plan-consolidation`。[计划树](design/universe-i21-native-import-plan.md)审定SHA12e964370403c52b36e65ebe4a96f4dae3ee554b40fe1e6239a5ed7224dd9f97保持原字节；[统筹结算](evidence/universe-I21R/report.md)。源资产未改，未改主checkout；无新goal。

| 节点 | owner / branch / worktree | 状态 |
| --- | --- | --- |
| P0 | root + i20_assets_plan + i20_universe_plan | complete；两位旧agent只读调查发布版导入API和呈现交接边界 |
| C0 | i20_review | accepted；最终12e96437方案，准许冻结和派发A；准确代码/argv仍须C1接受后才运行UE |
| A | i20_assets_plan；codex/i21-import；.worktrees/i21-import；base6eae279 | partial；执行源3b156d5的5CPU/真源preflight/C1通过，Native失败；后续guard-only及更正文档tip cd3b26f，仅AST/静态接受，未UE验证。[草稿PR130](https://github.com/Volc-yang/edging/pull/130)已发布、未合并；用户明确授权后原子推送三分支，原拒绝历史保留；CI42772541288 completed/success（仅Ubuntu自动检查），不授Native门 |
| R | root | partial；实际2import，首次监督器拒绝诊断项主动终止，第二次wait255/None.enable_section_collision；两Host Content空、uasset0。未派reload/第三次。终fsync742.467523s/26,383,495B、进程静默/源不变；首forced及UBT三项外域变化不覆，组合门fail |
| C1/C2 | i20_review；codex/i21-review；原.worktrees/i21-review；base6eae279 | complete独立裁决；source2f434cb→root审读后-x摘取763f963；21个报告原件/索引相等。两准确卡/813唯一pins、34个I20源原件、7份runtime副本、完整quiet/外域差异复核；D3-IMPORT NOT ACCEPTED。root稳定路径重放同一结果；C树干净/无运行依赖后已non-force移除，源分支保留 |

实际两次卡/源/日志/资源与失败分析见[完整报告](evidence/universe-I21R/report.md)及[原件索引](evidence/universe-I21R/runtime-evidence-index.json)。`content_bytes=2,679,781`为DDC/Content的两份.udd保守计量，不是已保存原生资产。没有Native正例/故障注入/reload或UE画质通过；无Universe/worker/Genesis，不改GameMode。D3-ADAPTER/准确C++构建与D4 Metal实拍继续依赖真实metadata。I18/I19/I20裁决及未知Dot候选保持。

Worktree使用仓库固定`.worktrees/<task>`规则（app managed工具未提供固定目录参数）。A树因Native失败/未集成保留；已结算C树按等效证据审查门和[实际清理](evidence/universe-I21R/worktree-settlement.json)移除，原分支与全部报告已推送保留。主checkout仍d6298e3，用户修改、I15/I12B和历史树、DevSSD原件保留。没有强制清理或把未集成源当基线。[父级稳定路径复核](evidence/universe-I21R/parent-check-01/receipt.json)确认原件和C2一致，不授Native通过。

下一步：从A的cd3b26f/草稿PR130明确命名为前置输入，先审新卡的公开`unreal.load_module('StaticMeshEditor')`及真实能力先检；明确Nanite源/render/fallback计数策略后，新root/新预算导入并独立reload。旧guard+旧preflight不授权新Native卡；不重复I20下载/合同轮。[公开授权与实际发布回执](evidence/universe-I21R/publication-receipt.json)已记录，失败A不能合并；CI结果与Native门分账。
