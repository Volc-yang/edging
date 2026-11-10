# Pull Requests 审查入口

用户已要求新增独立审查会话并执行审查后的合并。
会话 ID：`01a1c4c5-5809-79c2-ae72-2fa4b70ee845`，host `local`。
该会话负责独立代码/证据审查；统筹会话负责串行执行与合并，防止重复操作。
不创建定时任务，不将当前授权扩大为无条件合并以后所有 PR。

| PR | 准确输入 | 当前审查与动作 |
| --- | --- | --- |
| [130](https://github.com/Volc-yang/edging/pull/130) | public head768b1ac；proposed headfcf6895/tested sourcedf1863e；target codex/plan-consolidation实际ref5f2bbe3，PR API base_sha9d24a9c不能当target tip | 本地源码approved、C2/D3-IMPORT已通过：file_map已修，真实5/14/3、22包、负例、独立reload/资源门均过。[C2](evidence/universe-I23R/C2-independent-review.json)。新head push被自动审批以固定公开清单不覆盖为由拒绝，保持draft/未合并，等待新精确payload公开许可后push→准确headCI/ref→合并；不再重复Native。 |

合并必须核对准确源码、测试/CI、独立审查、必需原件、目标ref与最新head；
出现缺口只重开受影响项，保留失败记录。不能用mergeable、CI或用户合并授权
冒称缺失的真实阶段门通过。主checkout用户改动及既有恢复/构建树保留。
