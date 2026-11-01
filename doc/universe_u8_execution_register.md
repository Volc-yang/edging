# U8 规模与质量预算：执行登记

状态：2026-11-01，v0.1，进行中；parent=U。依据[架构树](universe_architecture_design_plan.md)和[U4 接受记录](design/universe-u4-integration-review.md)，用户授权继续下一步设计，不是授权正式压力运行或批准产品阈值。

## 固定任务卡

- 基线 `fb93c291fc594086c0115294e731e7501434b7c7`；depends_on U2 `b78b3ab`、U4 `28122b7`、U6 `95903b2`、U7 `38f8e02`，均已接受为版本化设计输入。
- Owner `/root/u7_projection_design`，非作者只读 reviewer `/root/u2_physics_design`；主统筹做局部集成 Check。本次不替代 U9，未来 U9 reviewer 不得是 U1–U8 的交付 owner。
- 真实仓库 `/Users/yangacan/edgeWorld/edge-world`；worktree `.worktrees/u8-universe-scale-quality`；分支 `codex/u8-universe-scale-quality`；PR target `codex/plan-consolidation`。
- 独占写 `doc/design/universe-scale-quality.md`；只读既有契约、报告、采样脚本及必要系统元数据，不改产品/UE配置/worker/其他文档或主工作区。
- Plan/Do：给有界负载、指标/单位/采法/样本规则、provisional 候选阈值、资源预算/中止条件及分阶段放行；区分当前环境观察、用户批准目标、未来运行实测。
- Check：owner 单文件范围/链接/差异自检；reviewer 核对各门可判失败、缺证不通过、延迟与吞吐/统一内存/正确性/历史和恢复边界；统筹核对 U2/U4/U6/U7 输入及最终 PR/CI。旧 600 帧信号试采不是新负载性能证据。
- Act：最多两轮定向修订；接受仅放行 U9 最终审查与实现树，不把未批准的数值或候选资产升为产品验收标准。
- 资源：一份主设计；不启动 UE/Genesis/GPU/压力/模型、不安装依赖或下载资产；普通 scoped commit/push/独立 PR，禁止自 merge 或重写已发布历史。

## 当前状态与收尾

工作进行中；PR 未建；owner/独立设计/局部集成门 planned；全部新运行门 planned；worktree 活跃保留。最终逐项记录 exact source、PR/merge、实际检查和限制；通过 CI/审查后按 expected head 合并，干净且 source 为集成祖先才清理任务 worktree，保留分支/报告，更新 backlog 并 commit/push。U9 仍等待 U8，U 总轮和 V-HOME 产品总门保持开放。
