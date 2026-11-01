# U9 最终跨卡审查与实现树：执行登记

状态：2026-11-01，v0.2，本卡完成；本次 U 设计轮收尾；parent=U。依据[架构树](universe_architecture_design_plan.md)，U4/U8 依赖及 U1–U8 局部设计门已接受，用户授权继续总审查。本卡不是实施放行或产品验收。

## 固定任务卡

- Owner/reviewer：全新 `/root/u9_architecture_review`，未承担 U1–U8 任何交付；主统筹另做本卡集成检查，既有 leaf owner 不能替代最终独立 reviewer。
- 基线 `4bb7452115763bbe02534850edb95a20f3e8afb0`；直接依赖 U4 `28122b7`、U8 `98890ba`；同时逐份审查 U1–U8 及原局部复核，而不是直接复用先前裁决。
- 真实仓库 `/Users/yangacan/edgeWorld/edge-world`；worktree `.worktrees/u9-universe-integration-review`；分支 `codex/u9-universe-integration-review`；PR target `codex/plan-consolidation`。
- 只允许写 `doc/design/universe-integration-review.md`；其他设计、代码、配置、旧档与用户主工作区保持原状。可只读相关实现与证据。
- Plan/Do：需求/接口/owner/正反例/证据/门与未决追踪矩阵，跨卡身份/时间/权威/事务/投影一致性及 DAG 审查；合成一条同世界“初态→物理候选→提交→UE观察→退出重访”场景，AI 为未来可选分支。产生下一轮可独立派发、路径独占、有固定前置和验收的实现任务树。
- Check：用户决定无偷换、引用/哈希及依赖无环、写入归属无冲突；未冻结接口/预算不直接放行生产实现。设计阻断先报告最小返工节点；文本/链接/DAG 检查与未来运行门严格分开。
- Act：最多两轮定向修订；接受须由统筹核对 exact diff、追踪矩阵与独立 PR/CI。本卡通过只关闭本次架构设计轮的检查义务并给出分级放行，不关闭 V-HOME 或整个产品开发。
- 资源：一份审查/实现树文档；不运行 UE/Genesis/GPU/压力/模型，不安装依赖/下载资产。普通 scoped commit/push，独立 PR，不自行 merge 或重写已发布历史。

## 实现树最低要求

叶卡记录 ID/parent/depends_on、owner角色、固定输入、独占具体路径、P/D/C/A、预算、中止条件、正反例与原始证据、ready条件。首先安排技术契约与可执行fixture，审查后才并行无GPU的存储/锁/幂等/恢复；物理扩展、UE接线及组合采证仍需各自明确前置。世界法则、实际schema与存储profile、资产、性能/规模数值的冻结责任不遗漏，也不将待决项无限推给另一份笼统设计。

## 当前状态

工作完成；PR [#76](https://github.com/Volc-yang/edging/pull/76) merged；source `72450e3a99c2733f3d729b909372b5778da0d5f4`，merge `047b89f5c356b094f9062776dc57f6b3e643f8c5`。15链接、8输入祖先、25节点54边增广DAG与13卡42路径检查通过，最终CI verify SUCCESS；独立架构审查和统筹集成设计门pass，所有新运行门planned。见[统筹收尾](design/universe-u9-coordination-review.md)。确认干净/source祖先后已清理任务worktree，分支/报告保留。U1–U9本次设计轮义务完成，产品总计划仍开放；唯一下一ready为I0技术契约与可执行fixture，尚未派发。
