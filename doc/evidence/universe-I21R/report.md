# I21 统筹结算：真实导入门未通过

2026-11-10；统筹root，固定计划6eae279/原输入d5ada8f。**本轮有界运行已结束，D3-IMPORT未通过；没有保存的UE资产包，没有Native快照/负例或新进程reload通过。**用户明确授权后已公开推送并创建草稿PR130，整轮保持partial，不能称集成或画质完成。

## Plan / Do

[独立审定方案](../../design/universe-i21-native-import-plan.md)的SHA仍为12e964370403c52b36e65ebe4a96f4dae3ee554b40fe1e6239a5ed7224dd9f97。目标为独立content-only Host导入5个mesh、14纹理和3材质，保存后由第二进程重新读取真实属性。UE5发布版/插件优先，没有修改引擎源码。A/B两位planner完成只读调查；A实现，C独立审查，root唯一实际运行；没有新goal、UI人工操作、worker/Genesis或Universe会话。

| 节点 | 准确身份 | 结论 |
| --- | --- | --- |
| P0/C0 | 6eae279；[计划接受](plan-review.json) | complete，仅准许按C1准确卡执行 |
| A 代码/CPU | 初版c71664b→受审执行源3b156d51cc9df110e5ef24e0be82618d54e2eb5b | 5项CPU与真源preflight独立复核通过；实际Native导入失败；已建草稿PR130，未集成 |
| A Act | guard-only a0ebfbf→文档更正后本地tip cd3b26fde5655b77482daa051eb2eb00c2c55359 | 在任何资源修改前明确拒绝缺subsystem；AST通过，尚未UE验证，不使用旧preflight授权新源 |
| R import01 | [卡](import-01-card.json) f5b9acfe…0731；原driver1054f93a，PID10196 | 监督器拒绝诊断非regular项并主动终止；parentwait0但forced=true、normal=false；不是正常导入成功 |
| R import02 | [卡](import-02-card.json) 11c3a555…484f；v2 driverdbc47f6a，PID26198 | 实际执行Interchange/Python；parentwait255、非强制、后代静默；None.enable_section_collision，保存前失败 |
| R reload | 未创建/未派发 | import未通过，不能把第三次导入伪装成reload |
| C2 | source2f434cb0945df483daeb3eb51dbf3ab29cd5f98c→root摘取763f9639ff2b490faefe152671fc1aac7a37d1d8 | root审读[独立报告](../universe-I21C/report.md)并逐字节核21个文件/索引；稳定路径重放同一拒绝Native/partial结果，无实现PR合并 |

A实际执行源与最新guard不是同一版本。所有运行脚本在DevSSD的a1/a2独占快照，不依赖A临时源码被覆盖。原driver/seal和两张卡均保留原路径与原字节；v2使用另名文件，不使首轮800pins失效。A没有启动UE或写DevSSD；C没有启动UE或改DevSSD。

## Check：两次真实失败与资源

1. import01的Cmd本体在PS中持续存在，启动了Build.sh→dotnet/UBA的自动平台SDK检查。监督器的regular-only计量拒绝`a1/tmp/dotnet-diagnostic-*`并主动SIGTERM；原结果未保存该瞬间lstat mode，因此不冒称独立测得Unix socket类型。完整日志没有Python执行标记。Mac SDK VALID与Win/Linux缺SDK属于AllPlatforms查询，不能当成本次失败原因。原[execution](import-01-execution.json)的forced/normal失败保留。
2. root窄修另建v2，仅允许精确owned tmp内实际lstat确认的dotnet诊断socket并记录类型/bytes，不读取IPC，其他特殊项和Content仍拒绝。另按安装源码、独立C1明确只为a2设置`UE_SKIP_UBT_SDK_SETUP=1`，不修改原dispatch、不授SDK/build门。IPC绑定测试在sandbox EPERM，未称实际类型分支已测通过。
3. import02实际执行约26.407s，已在内存执行网格/纹理导入及材质创建；随后`get_editor_subsystem(StaticMeshEditorSubsystem)`返回None，调用`enable_section_collision`失败。[实际FAIL](import-02-native-failure.json) / [父进程与监督原件](import-02-execution.json)。两个Host的项目Content均为空，无`.uasset`；保守`content_bytes=2,679,781`实际来自a2/ddc/Content中的两份`.udd`，不能当作已保存资产。Native正例/故障注入/reload均未到达。
4. [封存](campaign-seal.json)后由实际工具stdout记录[post-fsync观察](post-seal-tool-observation.json)，来源见[捕获说明](post-seal-tool-provenance.json)：连续742.467523125秒、新root26,383,495B、保守Content计数2,679,781B，低于900s/4GiB/512MiB；自有进程静默、输入终检无错。**资源/正常完成组合门仍失败**：首次主动终止，且[声明六外域差异](external-diff.json)有UBT三项元数据变化（含Trace.uba），不回写成pass。没有第三次import、没有新clock或隐含重试。

[七份逐字复制的runtime原件及SHA](runtime-evidence-index.json)可与DevSSD原件重比。完整UE日志、PS与before/after元数据留在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import`，不把含主机/login信息的完整日志复制进Git。source I20A全部20payload保持原SHA；没有新的权威状态/物理/画质验收。

父级在稳定统筹树763f963实际调用已审只读C2 verifier，813个唯一pin、34个I20原件、两次quiet与final PS、七份副本及资源/外域结果与独立C2逐项相同，21个C交付原件/索引SHA一致。[实际父级receipt](parent-check-01/receipt.json) / [完整输出](parent-check-01/stdout.txt)。exit0仅表示不变量/原件复核成功，任务裁决仍为D3-IMPORT未接受；没有重复启动UE。

## Act：最小纠正入口

缺subsystem的最强解释是所属动态Editor模块尚未启动，不能仅凭头文件/反射类型存在推断实例可用。下一卡先用发布版公开`unreal.load_module('StaticMeshEditor')`验证模块激活，再在任何资源改动前检查真实subsystem及必需getters。其StartupModule会加载AdvancedPreviewScene，应纳入准确模块pin/NullRHI预算；deprecated库仍转发同一subsystem，不作为兜底。若该路径不适用，再比较已安装引擎的其他受支持入口，不改引擎源码。

另一个待纠正语义是Nanite：安装pipeline默认启用，a2确有NaniteBuild；`GetNumTriangles(0)`读取render/fallback，不等于原glTF三角数。后续方案必须明确Nanite策略，并分别记录source、native render LOD0、Nanite input；不调大容差或改源fixture来伪通过。A的下一卡建议先显式关闭Nanite完成最小几何验收，最终视觉策略另审。

下轮第一步是审定“模块激活/能力先检→明确Nanite计数语义→新独占导入→保存/Native负例→独立reload”纠正卡，使用新预算并保留I21全部失败。GameMode原子HUD/scene、运行profile、C++build和Metal画质依赖导入门；继续planned/not run。

## Git / 发布与保留

公开目标经fresh GitHub connector核实为同账户Volc-yang/id56686828的公开仓库Volc-yang/edging/id1291093087、admin/push=true。A此前推送两次被自动审批拒绝，要求用户明确确认本批代码、本机路径、引擎元数据和哈希可公开发布；未换渠道绕过。完成本地交付、实测、审查与固定清单后，用户明确回复“允许发布并建草稿 PR”。按此授权原子推送统筹9d24a9c、A cd3b26f及C 2f434cb三个分支，创建[草稿PR130](https://github.com/Volc-yang/edging/pull/130)，head/base身份核对一致；未合并。CI42772541288 completed/success；仅Ubuntu自动检查通过，不授Native/画质门。[授权/推送/PR回执](publication-receipt.json)保留完整边界。原[清单](public-payload-manifest.json)仍绑定9d24a9c快照，当前仅追加发布状态元数据，不改旧运行原件。

远端已保存统筹结算9d24a9c及A/C源分支；A `codex/i21-import`保留cd3b26f/草稿PR130，未合入统筹分支。root只保存本轮执行/审查/上下文及发布状态，不带入主checkout改动。A未通过任务树保留用于纠正；C的21文件已等效审查/摘取并完成父级复核、无运行卡依赖，干净树non-force移除，原分支/源commit已推送。[准确worktree结算](worktree-settlement.json)。所有DevSSD原件、I15构建树、I12B恢复树保留；没有reset/clean/stash/强制删除。主checkout仍d6298e3。I18 exact3、I19/I20裁决和未知Dot候选状态不变，未联系Dot、未改网站/DNS/API。
