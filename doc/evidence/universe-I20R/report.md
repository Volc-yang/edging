# I20 统筹结算

2026-11-10；父任务 `/root`；分支 `codex/plan-consolidation`，稳定树 `.worktrees/plan-consolidation`。**接受本轮A/B/C有界交付并关闭本轮；写实产品目标、D3/D4仍开放。**用户允许引入开源模板并授权询问Dot；可用工具无可寻址Dot入口，请求未发送，D0延期，不冒称找到了Dot的592项候选代码。

## Plan → Do

[冻结方案](../../design/universe-i20-realistic-pdca-plan.md)于6c533af经独立审查接受：并行取得小型许可资产输入、制定独立Universe只读呈现合同，之后独立与父级集成检查。本轮明确不运行UE/build/GPU/worker/Genesis/UI；后续导入/实现和实拍另卡。未建立或恢复goal。

| 交付 | 最终源 / 集成 | 实际结果与限度 |
| --- | --- | --- |
| A 资产输入 | [PR128](https://github.com/Volc-yang/edging/pull/128)，30907e8dd645cb1b7c3580cf101f180b77b47865 → a3ca6a423d15b99bd73f0c7d37f7ad502741021e | 源/许可/依赖门接受；20个实际payload、41,949,796B；不是UE资产或画质通过 |
| B 呈现合同 | [PR129](https://github.com/Volc-yang/edging/pull/129)，d6fe60de9c3ad9fad837841f2bd3bfb027a90896 → 0dfde3e248cd1e0f480b3d83a02351363b69db7b | 独立profile、ViewBinding、schema/语义检查及D3/D4卡；仅合成CPU合同接受 |
| C 独立审查 | 3627af2df70bee1b05ab824640e535742f0e7ea9 → 6996d714f3ec9d40dd7ef1ff09f9d69ce1cddc56 | 按父任务证据交付，root审读后直接`cherry-pick -x`保留出处，非实现PR；14个报告/原件逐字节验证，未另跑文档全CI |

A/B的最终CI均为真实completed/success：A [42753910052/run174](https://github.com/Volc-yang/edging/actions/runs/42753910052)，B [42754957084/run176](https://github.com/Volc-yang/edging/actions/runs/42754957084)。查询和merge父提交见[GitHub/集成记录](github-integration.json)。只合入统筹分支，没有同步或合并到本地feature/edge-world。

## Check

三层检查分别留存，不以PR或自报完成代替父级接受：

- A owner实际校验源MD5/SHA、glTF闭包、几何范围及负例；独立C逐字节复算28个响应体42,116,535B、确认145.218854s/256MiB/64files/20min上限、14张2K纹理完整解码及4个拒绝负例。root合入A后实际重跑verifier exit0/PASS；[完整结果](integration-source-check.json) / [收据](integration-source-receipt.json)。
- B初版14项自检通过，但独立C发现合法JSON `1e999`会成为无穷float。仅返工该叶的解析及API字典有限数检查，补1项回归；最终owner15项、C重跑15项及5项额外定向检查通过。[独立报告](../universe-I20C/report.md)同时保存原失败和修复后拒绝，旧结果不覆。
- root在稳定统筹树6996d71实际比较A的23、B的13、C的14个交付原件；核对方案固定SHA、审查原件与B最终收据、两个阶段源文件及不可变Git blob。34个DevSSD文件与早前root索引再次一致，运行树无临时worktree引用。最终稳定路径15项测试实际exit0/unittest0.485s，subprocess wall0.574s。[父级机器结果](parent-check-01/integration-check.json) / [完整输出](parent-check-01/contract-check.txt)。

父级检查可用[脚本](check_integration.py)重现，参数必须为新的输出目录；脚本只读源文件，在参数目录保存新原件。B测试环境为 `/private/tmp/edgeworld-i20b-contract-env`；其版本/下载身份已在B锁定，需要重建时仅重建隔离CPU环境，不改项目或用户环境。

## Act：接受范围、清理与下一入口

真实源组合保存在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets`，index SHA为 `d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7`。许可结论仅覆盖该Poly Haven来源的CC0模型/纹理，不能泛化为模板代码、商店资产或其他包。Electric Dreams仍是DX12视觉参考，未作为Mac/Metal可运行开源包引入。

必须保留的D3事实：蕨叶RGB JPEG没有alpha，须连接独立灰度Alpha PNG至Masked/OpacityMask0.5/TwoSided；原glTF的GL法线保持原件，DX图由显式UE recipe覆盖并检查方向；ARM通道与sRGB需真实Native核对。地表glTF为预览球，不能成为世界地形，应将其纹理用于批准派生平面。六个旧Cube是场所marker，不能统一替成树。

新呈现是独立opt-in `realistic-readonly-sidecar.v0.1`，保留旧authority的 `basicshapes-proxy.v0.2`。当前GameMode先改Session后ApplyVerified的HUD/场景混片风险尚未修复；D3同一呈现owner必须实现隐藏装配与已呈现binding同次提交。B正例全部synthetic、Native metadata unresolved；不存在可运行真实profile或Native真实性放行。

A/B/C三树清理前均干净，所有交付已合入或按原字节保留；实际输入在稳定仓库/DevSSD，分阶段映射解决A历史receipt旧路径，不重写旧记录。三次 `git worktree remove` 均exit0，无force；保留所有分支、DevSSD资产、I15构建树/I12B恢复树及其他历史树。[前置检查](worktree-cleanup-preconditions.json) / [实际清理](worktree-cleanup.json)。主checkout仍为d6298e3且保留全部用户改动。

下轮先按[已落盘任务卡](../../design/universe-realistic-presentation-profile.md)审定执行树和明确新预算：D3-IMPORT取得真实UE包/依赖/class/units/pivot/bounds/slots及材质证据 → D3-ADAPTER实现profile/原子HUD和场景 → D3-BUILD准确源码官方编译 → D4新卡真实Metal原生PNG/当前历史只读/正常退出及画质性能。任务卡已保存，尚未派发；未满足的Native、平台、事务、画质和性能门继续planned/not run。

I18 exact3的有限接受、I19终端接线失败、旧全部失败账保持；没有改旧authority/parser/worker/I0A或引擎源码，没有新运行/网站/DNS/API路由变更。上下文通过本轮限定文件的结算commit保存；提交SHA以Git历史及本轮反馈为准。
