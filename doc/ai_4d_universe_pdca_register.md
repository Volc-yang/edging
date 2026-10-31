# 4D 世界游戏 PDCA 开发框架任务登记

统筹分支 `codex/universe-pdca-master`；输入基线 `abc990a`；主计划 `doc/ai_4d_universe_pdca_master_plan.md` v0.2。这里管理**开发过程任务**，不制定玩法/世界规则。

| ID | owner / 交付 | 依赖 | 状态与下一门 |
| --- | --- | --- | --- |
| F0 递归框架 | `/root/universe_p0`；`doc/pdca_f0_framework_proposal.md` | v0.2 总计划 | 已派只读方案；待固定新基线后在独立 worktree 写报告与 PR |
| F1 质量与证据 | `/root/pdca_f1_quality`；`doc/pdca_f1_quality_proposal.md` | v0.2 总计划 | 已派只读方案；待固定新基线后在独立 worktree 写报告与 PR |
| F2 编排与上下文 | 主任务；`doc/pdca_f2_orchestration_plan.md` | F0、F1 的审查结果 | 待启动；定义任务/对话/worktree/PR/反馈路由 |
| G0/G1 | 后续技术任务 | F0–F2 冻结 | 未派；将用户产品目标转为版本目标及技术接口，不由 PDCA 自动推导玩法 |

曾创建两个用户可见的新对话：`01a1940d-d93b-7a30-9dc8-0af14e21eb01`、`01a1940d-d3a4-7210-a683-454e389eebe4`。两者创建后立即因 Codex 应用默认模型 `gpt-5.5` 在当前 ChatGPT 账号不受支持而 `systemError`，**没有执行任务、没有创建工作树或提交**。旧提示还误指向产品契约，已撤回；不得将这两个对话算作完成或继续按旧卡执行。F0/F1 暂由当前会话 subagents 执行。新对话恢复后应使用修订任务卡，并检查模型配置。

每个任务记录实际提交、独立 PR、Check 证据、Act 裁决和 worktree 清理。规划报告不自动成为批准的开发流程；主任务须审查并集成。
