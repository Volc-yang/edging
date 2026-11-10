# I23 / PR130：真实资产导入与独立重载

目标是完成用户要求的 PR 审查与合并。独立审查会话
`01a1c4c5-5809-79c2-ae72-2fa4b70ee845` 已完成 C0、准确源码/执行卡 C1；
root 实际完成 probe → import → reload → seal，父级只读回放通过。
**独立 C2 与 D3-IMPORT 已接受，PR130已合并到codex/plan-consolidation**。
用户明确批准新增固定公开清单后，fcf6895/0540802原子非force发布，准确head的
CI180/181均success，最终独立审查approved，以expected head合并为90c3a53。
[合并回执](merge-receipt.json)保存授权、远端核验和实际双parent；旧审批拒绝原件保留。

## 源码与审查

准确执行源码 `df1863e900ad7b96c36dc05507ac221d6ab5ab25`，基线 PR head768b1ac。
修复了 file_map 静默忽略非普通项的问题：严格扫描/lstat/读错误传播、拒绝
链接/FIFO/socket/device、必需根缺失不当空成功，普通目录与文件映射保持。
NOFOLLOW/NONBLOCK/fstat 防替换成链接或阻塞项。9CPU、AST、diff 及独立9CPU通过。
真实链接/FIFO有回归；socket/device采用lstat类型注入，sandbox首次AF_UNIX
拒绝记录留在A证据中，不把类型注入说成UE或真实socket执行。

新 OUTPUT 使用 I23 独占目录；保留 I22 ABI/包路径、来源、三角数与AABB容差、
独立Alpha、显式DX法线、ARM通道和Nanite=false，不改引擎源码/既有世界。
[冻结方案](../../design/pr130-merge-validation-plan.md)、[C0条件](C0-addendum.json)、
[首卡C1](C1-acceptance.json)、[准确晚绑定审查](C1-late-card-reviews.json)。

## 实际结果

原件根：`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import`。
固定 UE5.8.3 CL58210709、I20原件及已审recipe。三阶段都由root真实Popen/wait，
均exit0、非forced、无cleanup、后代静默，输入与独立job身份终检通过。

| 阶段 | 实际PID/parent | Native result SHA | 结果 |
| --- | --- | --- | --- |
| probe-01 | 87036 / 86874 | 971c6fb127c3ad4b6d69915855bcf906b62ebd70f32860e62145c9f9bbe5a312 | 临时mesh/texture/material真实调用与全字段恢复、原Engine getter/包、空Content文件图通过 |
| import-01 | 96593 / 96513 | e2af513bd11eb912539bbd3746e7bf70e9e514541dbef141f092a68d97f69bbc | 5 StaticMesh / 14 Texture2D / 3 Material，保存22包39,910,827B，严格来源/几何/材质/slot与两项真实负例通过 |
| reload | 11448 / 11419 | fb7cd5fb53ce57d9d1a0cfa11d0c249a96d66c30b2b88ca73e42a22de9ab30b1 | 全新进程，同Host/Content、独占session；完整Native快照等于import，真实负例再次拒绝/恢复，Content全部字节不变 |

Alpha实际断开后getter=None，被准确拒为material source mismatch opacity_mask；
实际fern slot换成boulder材质，被准确拒为mesh slot material mismatch。两项均
恢复，未保存故障；严格snapshot通过。ground预览球没有当作地形导入。

## 封存与父级复核

原seal SHA `cf2cf5e3725376ad64f1d7480d2139a92a94e6229ad717863a0f50fb99e51bb8`，
原post-fsync工具stdout [另存](post-seal-observation.json)，连续
**492.531216541秒 <1200秒**，outerexit0；root **77,341,675B <4GiB**，
项目Content **39,910,827B <512MiB**，DDC **13,293,053B**单列且计总量。
每阶段时限+至少30秒封存预留保持；实际仅1probe+1import+1reload。
封存后没有运行根写入；原始UE/PS日志和资产二进制只留DevSSD。

`check_parent.py` [实际回放](parent-replay.json) exit0，重算904唯一输入pins，
核对完整成功选择链、真实父wait/原始quiet/final进程清单、22包完整图及正/负例、
六声明外域集合/exists/entries不变、34个I20原件与274个I22原件逐字节不变。
源码/安装inventory/准备器副本/全部包与sidecar均按准确卡固定，不能只以CI代替。

本结果是 content-only / NullRHI 导入与持久化门，不授Metal画质、运行时、
复杂生态、Genesis物理或完整4D世界验收。主checkout和其他构建/恢复树保留。

## C2 与当前合并入口

独立审查在turn `01a1c4e3-be09-7722-8499-0d4ae69334b9` 接受D3-IMPORT，
[原报告](C2-independent-review.json)逐字节复制自临时交付，SHA
`a59b9c8b1a7baed3f602fdf4604e814e8be37390eba1da080e9115b27ec62e22`。
独立复核904pins、38进程样本、9quiet与final、427普通文件、22包头/字节、
两进程故障getter与恢复；直接从固定glTF accessor重算5mesh三角数和AABB，
最大误差1.6689300537e-6cm，小于原0.02cm容差，未改契约。

A最终head `fcf689522598dcbb9cac367521ddeb053cb49e4c` 相对实际源码df1863e
仅更新I23A报告。审查会话在turn `01a1c4e8-452b-7b81-b9a8-0cadf1970dbb`
核验生产源码/测试字节未变，沿用Native接受，不需重跑UE。
源码树干净但尚未合并，按工作流保留，见[worktree结算](worktree-settlement.json)。

此前首次发布尝试曾在进程创建前被自动审批拒绝，认定PR合并要求未明确覆盖
旧I22固定清单外的新payload，见[原拒绝状态](publication-status.json)。当时停止
所有新公开动作，没有改走API或强行merge，远端仍768b1ac。随后完成精确清单与
本地0540802提交，用户明确回复“允许发布并合并”；正常git原子发布后，准确
head CI/ref与最终独立审查通过，执行转ready及expected-head merge。本次授权
已解除该发布缺口；原拒绝记录作为历史保留，不表示当前仍待许可。

实际合并及后续上下文仅包含已批准内容和结果元数据；统筹稳定树已快进，生产源码/测试
与Native执行df1863e字节一致。源码工作树因冻结准备器的源验证引用暂留，见更新后的
worktree-settlement.json；不因合并删除复现依赖。主checkout与其他原件不动。
下一轮应进入已保存资产的只读运行时呈现/Metal验收，而非重复D3导入。
