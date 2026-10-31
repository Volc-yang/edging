# Agent 协作入口

开始本仓库的新迭代或并行任务前，必须先阅读 [`doc/parallel_agent_workflow.md`](doc/parallel_agent_workflow.md) 和最新的 [`doc/parallel_execution_backlog.md`](doc/parallel_execution_backlog.md)，再查看适用的开发计划、阶段报告和 Git worktree 状态。

统一架构原则：优先使用 UE5 发布版的成熟引擎与渲染能力，通过插件/适配层连接 Genesis 和 edgeWorld 第四维状态演化。只有当发布版方案对已批准 4D 契约的实测不满足时，才评估引擎源码改造；源码改造须经统筹任务审阅证据、替代方案、成本和许可影响。

工作区含用户可能保留的未提交改动。禁止为了让任务变干净而 reset、clean、stash、覆盖或提交不属于本任务的修改。各子任务必须使用独立 worktree/分支并遵循工作流文档规定的发布、反馈、集成和提交步骤。
