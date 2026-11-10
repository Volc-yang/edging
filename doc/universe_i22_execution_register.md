# I22：纠正Native导入入口

2026-11-10；in progress。上下文545117d；source前置为未合并的cd3b26f/PR130。[计划](design/universe-i22-import-correction-plan.md)已独立C0接受，SHA0ebce94464c98becd8297833ab574b698dc9118363f5fedaafd9297761cb6f24；尚无真实UE，旧I21失败不改，无goal。

| 节点 | owner / branch / worktree | 状态 |
| --- | --- | --- |
| P0 | root + i20_assets_plan | complete，只读提案已纳入显式模块激活/真实能力和Nanite计数 |
| C0 | i20_review | accepted；[计划门](evidence/universe-I22R/plan-review.json)，准确source/card仍须C1 |
| A | 原codex/i21-import / .worktrees/i21-import @cd3b26f | queued；仅C0后开始，复用草稿PR130 |
| R | root / .worktrees/plan-consolidation | not dispatched；I22新root，1200s/4GiB/项目Content512MiB，max2probe+2import+1reload |
| C1/C2 | 审定后codex/i22-review / .worktrees/i22-review | queued；root唯一执行UE |

用户已授权本轮项目源码/测试/路径及UE元数据公开并创建草稿PR；该授权已完成记录，不重复询问同一发布事项。Native未通过的代码不merge。主checkout用户改动、I15构建/I12B恢复及I20/I21全部原件保留。
