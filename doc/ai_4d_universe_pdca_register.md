# 4D 世界游戏 PDCA 开发框架任务登记

统筹分支 `codex/universe-pdca-master`；输入基线 `abc990a`；主计划 `doc/ai_4d_universe_pdca_master_plan.md` v0.2。这里管理**开发过程任务**，不制定玩法/世界规则。

| ID | owner / 交付 | 依赖 | 状态与下一门 |
| --- | --- | --- | --- |
| F0 递归框架 | `/root/universe_p0`；`doc/pdca_f0_framework_proposal.md` | `1f7e67e`；`.worktrees/universe-f0-framework` / `codex/universe-f0-framework` | PR #22，`7db8fa1`，合并 `8f6a068`；静态 Chaos/Realism 回放与 CI 通过；干净 worktree 已移除 |
| F1 质量与证据 | `/root/pdca_f1_quality`；`doc/pdca_f1_quality_proposal.md` | `1f7e67e`；`.worktrees/pdca-f1-quality` / `codex/pdca-f1-quality` | PR #23，`f4b3ffb`，合并 `9d1d418`；三级门与 V1→V2 回放、CI 通过；干净 worktree 已移除 |
| F2 编排与上下文 | 主任务；`doc/pdca_f2_orchestration_plan.md` | F0、F1 的审查结果 | 统筹提交 `ea79836`；与 F0/F1 及旧对话冲突案例作静态一致性检查，过程框架已采用；未作运行时测试 |
| G0 版本目标 | 新对话 `01a19418-3e20-76b1-aa61-fea521e721fb`；`doc/pdca_g0_version_goal_proposal.md` | `d589e66`；`.worktrees/universe-g0-goals` / `codex/universe-g0-goals` | 用户选择 `gpt-6.1-sol` 后恢复；PR #24，`b7f0319`，合并 `661a341`，CI 与独立文档审查通过；干净 worktree 已移除。**提案已集成，G0 门未接受**：目标环境、必需范围与阈值仍待冻结 |
| G1 技术接口 / GQ 证据基础 | 后续技术任务 | G0 门接受 | 未派；可只读调查，不由 PDCA 自动推导玩法 |

两个用户可见旧对话 `01a1940d-d93b-7a30-9dc8-0af14e21eb01`、`01a1940d-d3a4-7210-a683-454e389eebe4` 初次启动报默认模型 `gpt-5.5` 不受支持，随后异步执行了**已撤回的产品任务卡**，产生旧 PR #21/#20。两 PR 已关闭，旧 `.worktrees/universe-p0-contract`、`.worktrees/universe-p4-acceptance` 含未合并历史，干净但保留，不强制移除。旧对话已收到停止旧范围的消息。F0/F1 的正确交付由当前会话 subagents 在新的独立 worktree/PR 完成。以后创建对话必须再次确认实际状态与任务卡版本。

每个任务记录实际提交、独立 PR、Check 证据、Act 裁决和 worktree 清理。规划报告不自动成为批准的开发流程；主任务须审查并集成。
