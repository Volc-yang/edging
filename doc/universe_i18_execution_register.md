# I18：NoTrace Native 封存复测

2026-11-07；**complete，有限Native门pass**；输入a19ea4f，[审定方案](design/universe-i18-native-seal-plan.md)cf76b7a。N独立审查方案/[固定driver](evidence/universe-I18R/driver.py)/ready/实际原件接受，root集成后按稳定路径再次执行原verifier，coverage恰三份响应。仅复测已合入PR123/124修复，不新编译、不改产品工具、不重复CI；不是G-B2或Metal通过。

| 节点 | owner | 当前事实 |
| --- | --- | --- |
| 0 | root，i17_review独立审查 | complete；一次Native180s/global900s/2GiB，oldI17失败不覆，全部权限/ready在clock前 |
| P | root，N独立ready复核 | complete；复用Native/source5a6cca0全部source/binary SHA匹配，Native源无diff；tool ecc2f3d。prepared4192e0c0/cardbe612f03/manifestd798c9c8/inputs84292d4d/driverc46748a2逐项独立核验，DDC/controller新路径未存在，clock前完成 |
| R/T | root唯一运行owner | pass有限运行；真实一次UE10793/parent10778，四完整Success/case3接受、parentwait0/normaltrue；同一driver自动after完成，resource-review ea633257，21.290306s/1,586,779,592B/quiettrue/map不变/frozen原件一致 |
| A | i17_review，root发布复验 | pass exact3；原独立报告/机器review/policy/result commit4324369等价review集成49f35c8。稳定target verifier实际返回checks_complete_requires_review、coverage3、G-B2false，原成功契约未放宽 |

输出为原I15完整计量root下I18-20261107-native-seal新目录，DDC run/controller绑定短目录。复用旧owner/context/inputs/native/build，不读key或迁移世界；新run/tool/before_map/created_at变更另存provenance。声明六写域含Zen/UBT两域/DDC两域/Trace，均metadata-only before/after，非全OS I/O审计；若实际缺口仍不通过。用户主checkout、构建/I12B恢复树、旧goal及网站/DNS/API不改。

## Do / 当前实际证据

运行前审批完成后才启动完整driver，实际一次、未重跑。Native实际argv包含-notraceserver/-traceautostart=0、无$四叶前缀、固定GameModeBase/NullRHI及独占97字DDC。controller原resource为within_budget/allquiet/observer无error，writer barrier完成；outerwait0。同一driver在其后自动六域metadata diff、全部frozen fingerprint、61-file authority after、final ps与保守资源核算，未等待新的工具审批；root随后再次hash读取仍匹配。

已声明六外域只有UBT三项rotation/651B变化，Zen/全局DDC/Trace未变，metadataerrors0；root完整继承输出+当前外部changed files+65536封存余量1,586,779,592B<2GiB，driver elapsed21.290306s<900。原I17墙钟/晚写/actor失败保持，本轮不能替代全OS I/O审计或授Metal/G-B2。

## 独立 Check / Act

- N从37份actual rawps独立导出UE PID/start/parent，核对固定argv（含NoTrace/独占DDC）和四ENV、实际wait0无forced。Native17.556088s、controller19.556623s、outer19.904205s、完整driver21.290306s分别计量，不用小计遮全程；max observer gap0.566936s<2，writer barrier三新样本稳定1.117988s。
- 原三case所有五输入SHA/原request IDs/水位/Manifest-State-Event/selected31-42-45记录逐项匹配，实际Found4/四完整Success；不宣称新Genesis solve或真实键盘/PNG矩阵。
- 三frozen输出从barrier/seal/driver after/独立review到root发布复验均SHA/inode/time匹配，所有5个已观察owned identities最终静默，无sponsored Trace或Zen启动；61-file map及独立fresh map一致。独立root stat1,586,715,306B≤保守1,586,779,592B；六外域diff恰三UBT/651B。
- [独立报告](evidence/universe-I18A/report.md)、[机器review](evidence/universe-I18A/native-review.json) SHA9d3b8e1d458c524dc311b559e76bc8af56216b97bea7552847f7e7c240aaa941、[冻结policy](evidence/universe-I18A/native-policy.json) SHA6304d0686fb3ccb52af33912bdd7c8ee5ee5c60bdc554cabaa73d789b69713d8；root在稳定integration路径实际复验，[稳定结果](evidence/universe-I18A/native-verification-stable.json)返回checks_complete_requires_review/coverage3，结合独立审查接受有限门。

授权仅限这三份精确response SHA，旧legacy常量/API和其他未回放响应不静默升级；正式Metal/输入/原PNG/正常标准双会话及G-B2仍open。已知UE Dataflow Date初始化日志风险保留，不称所有UE启动日志无错误。没有新产品代码PR，因此本轮执行/独立文档按等价review集成，不冒称重复CI或重构建。

下一轮第一步：直接规划尚缺的**真实existing只读Metal呈现/输入/原PNG与正常退出**。沿已批准4D契约、UE发布版和原owner空grants，先冻结新范围/动作/预算/NoTrace-DDC及完整写域边界；当前Native的exact3覆盖不能自动授给新请求/响应。无需继续I18封存工具排查，旧失败与原件持续保留。构建/I12B恢复树仍被source/入口引用保留；review任务树已在报告/机器policy稳定路径集成、四文件逐字节一致、干净及81份公共运行文本依赖核对后non-force清理；[清理记录](evidence/universe-I18R/worktree-cleanup.json)，分支/DevSSD保留。[统筹结算](evidence/universe-I18R/report.md)及[244文件摘要索引](evidence/universe-I18R/runtime-evidence-index.json)已归档。用户主checkout/goal/DNS/API未改。
