# PDCA-CHAOS-02 任务登记

仓库 `/Users/yangacan/edgeWorld/edge-world`；统筹 worktree `.worktrees/chaos-pdca-02`，分支 `codex/chaos-pdca-02`，基线 `7cb65d2`。计划见 `doc/chaos_universe_pdca_02_plan.md`。

| ID | 负责人/状态 | worktree/分支/基线 | 交付与证据 | PR/集成/清理 |
| --- | --- | --- | --- | --- |
| H1 | `/root/chaos_h1`；实现完成、Metal 待 C3 | `.worktrees/chaos-h1` / `codex/chaos-h1` / `40567d7` | opt-in 控制入口；UE Editor/Game 构建、live NullRHI ack/O1、CI 通过 | PR #9，`9a78c58`，合并 `dffaccc`；干净工作树已移除 |
| V1 | `/root/chaos_v1`；实现完成，真实 Metal 待 C3 | `.worktrees/chaos-v1` / `codex/chaos-v1` / `40567d7` | 六类场所与路线代理；UE Editor 构建、fixture/seed7 NullRHI、CI 通过 | PR #8，`f556012`，合并 `52029e6`；干净工作树已移除 |
| C3 | `/root/chaos_c3`；部分完成 | `.worktrees/chaos-c3` / `codex/chaos-c3` / `dffaccc` | Metal 20 项逐项状态门通过；forest/marsh/ocean/route 视觉门失败；FPS 实测 cadence 未验 | PR #10，`f2dc889`，合并 `f1fb8f8`；干净工作树已移除 |
| V1R | `/root/chaos_v1`；实现完成、独立复测待 C4 | `.worktrees/chaos-v1r` / `codex/chaos-v1r` / `7d9288f` | OpenWorld 模板 Landscape 初始及流入隐藏；UE 构建、NullRHI、七区 Metal 先验图与 CI 通过 | PR #11，`38b52dd`，合并 `a187366`；干净工作树已移除 |
| C4 | `/root/chaos_c3`；完成（固定代理视觉门） | `.worktrees/chaos-c4` / `codex/chaos-c4` / `a187366` | 六区、河道及城市至海洋路线 Metal 画面可辨；9 项逐项权威摘要仅显式 O1 改变；CI 通过 | PR #12，`e910899`，合并 `363c2de`；干净工作树已移除 |
| A2 | 主任务；复盘完成 | 统筹 worktree | 技术控制/只读和固定代理视觉门通过；真实帧率 cadence、最终美术、跨平台与初态双次读取竞态开放 | 本登记及 backlog 上下文提交；统筹 worktree 保留 |

主工作区现有未提交改动及旧 PIE worktree 均不属于本轮。仅移除已合并且干净的本轮任务 worktree；原始大型画面证据在独立 Saved 目录保留。

下一轮入口：从本统筹分支读取 C3/C4 报告与矩阵；先决定“近乎完美”视觉目标的资产/地形/生态验收标准及预算，再为实际 Metal 帧时间计量、D3/D4 同源初态读取与跨平台 canonical hash 分别立界限清楚的任务。TWO 演化尚未启动。本轮集成仍未进入 `feature/edge-world`，不得把本地用户未提交改动带入集成。
