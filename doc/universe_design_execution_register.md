# U 架构设计：首批执行登记

状态：2026-11-01，v0.2，首批设计交付完成；U 总轮继续。父方案为 [U 设计树](universe_architecture_design_plan.md)，用户已批准执行下一步；本批范围为 U1/U5 的独立设计交付、审查与集成，不是 U1–U9 全轮关闭或产品实现。

## 固定输入与任务所有权

仓库 `/Users/yangacan/edgeWorld/edge-world`，集成分支 `codex/plan-consolidation`。两卡共同基线 `5a5fe11fc2c452de2aace7e8cc7c05d2fe5834c9`，包含已审查方案树；其引用的产品/技术证据基线 `f674483` 保持原身份。主工作区用户改动不动。每张卡为 v0.1、parent=U、depends_on=[]。

| 卡 | owner | worktree / branch | 独占交付 | 工作 / PR / 门 / 清理 |
| --- | --- | --- | --- | --- |
| U1 世界身份与因果状态 | `/root/shutdown_next_plan` | `.worktrees/u1-universe-identity` / `codex/u1-universe-identity` | `doc/design/universe-identity.md` | 完成 / #67 merged `da84aba` / 设计 pass / 干净且源提交已集成后移除 |
| U5 丰富混沌初态 | `/root/visitor_path_plan` | `.worktrees/u5-universe-origin` / `codex/u5-universe-origin` | `doc/design/universe-origin.md` | 完成 / #68 merged `89254ab` / 设计 pass / 干净且源提交已集成后移除 |

worktree 路径均相对上述真实仓库。已核对空闲分支、目标不存在和忽略规则，再从共同基线建立；用 Git CLI 是为遵循仓库固定 `.worktrees/<task>` 路径，应用 managed 创建工具没有指定父目录参数。

## 发布卡与 Check

两位 owner 已收到具体路径与输入，完整 P/D/C/A、正反例及未决项要求沿用父树。只读访问现有计划、相关源码和证据；只允许写自己的单份设计文档，不改 UE/worker/schema/配置或其他任务文件。每卡最多一份主设计及两轮定向修订；不启动 UE/Genesis、不占 GPU、不下载资产、不调用付费模型。

- U1：稳定身份/版本/时间、实体/区域/关系/灵域边界、字段与写权限、历史与因果、演化模块接口；分化/合流与具体世界规律保持开放。交付能为下游 U2/U3/U6/U7 提供版本化设计输入，不替换现有探针协议。
- U5：六类场所共存、候选连续路线及水系拓扑、生成清单/随机源、身份与视觉资产分离；固定 seed 示例仅验证提案内部自洽。具体地理和灵域法则不冒充用户决定；需要 U1 的身份字段先标接口待对齐。
- Owner 自检：本地链接可定位、正反例有预期结果、每个建议/既有决定/观察结果有标记与来源；只记录实际文档检查，未来运行门为 planned。
- 独立检查：主统筹为非文档作者，审查 exact diff、来源、反例和权限边界；必要时另派只读 reviewer。U9 最终跨卡 reviewer 不得是 U1–U8 的交付 owner。
- 父级集成检查：两卡的 world/region/身份及投影职责兼容；没有重定义现有 S4 wire、没有引入隐式推进；每个下游 ready 节点的依赖明确。每卡独立 PR 到集成分支，经审查与适用 CI 后集成，未审查不合并。

## 反馈与 Act

Owner 必须回报状态、准确 commit、PR、实际检查、限制及下一步；不得自行 merge。主统筹审查后逐卡接受设计或定向返工，分别登记集成 commit 和门状态。仅当任务 worktree 干净、源提交已合并且证据/报告已保留时移除，不强制删除。

本批结束更新 backlog、方案树和本登记并 commit/push。U1/U5 设计被接受后，U2/U3/U6/U7 可按接口依赖进入后续设计派发；产品实现仍须其独立方案和门。H6C 从 `f674483` 的独立运行不受本批文档影响；现 PR #69 / `0344827` 已合入，有限访客门接受，GPU 释放；V-HOME 产品总门仍开放。

## 本批结果

独立审查与集成 Check 见[报告](design/universe-u1-u5-integration-review.md)。U1 最终 `a7fed69`、U5 最终 `ec8bf6e` 各自 CI 通过、独立 PR 已合并，统筹复核旧 fixture 摘要、文档范围/链接及新候选图内部一致性；仅设计门 pass，新运行门 planned。两个本批任务 worktree 已移除，分支保留。下一 ready 为 U2/U3/U6/U7（尚未派发）；本批没有并行扩展产品实现。
