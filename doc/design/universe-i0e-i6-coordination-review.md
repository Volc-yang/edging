# I0E / I6 统筹接受与扩展派工（2026-11-02）

## I0E 精确格式契约门

PR #84，source `f13a73d588e3bdb2950403eecbabc3d48fe0b065`，merge `9ad01c36b96a802c218c1935088c5211dc36c094`。首check有负例错误码期望错误，既有per-kind上限先拒绝；未放松算法，唯一targeted check通过67golden/4root/57negative/5proof。受检算法source `168e5f6` 后仅contract/CHECK文档变化；完整原始失败/成功日志在fixture CHECK链接中。

非作者u9自行编写递归ASCII encoder/Fraction/HMAC复算，无导入owner oracle/生产codec：67字节/摘要、6MAC、4root、5proof、2份raw82B、264-source tree、record inventory和457728B proof cap算术一致。独立原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I0E-20261102-independent-attempt1/raw-index.json` SHA `da016768c07a79350c9fc833ec1da5c9af2b7bd81dfa9d1b3e775247d50de0d9`；root复算32/32索引文件size/hash通过。root与u9完整API/trust/proof审查闭合bootstrap循环、兼容默认、typed绑定/可信storage label、verifier不取secret、bounded graph与可消费DTO。最终head CI verify success（run41325496502/job124904448361）。接受 **G-C0.2技术格式/API门pass**，不是新模块运行门。

计量限定：S_records=30不等于U8 S_typed；typed差集已在独立原件列明（路/水段、嵌套binding、预算/RNG/规则等），alias/去重映射需I10完整枚举/规模准入前冻结。禁止把30与旧32/288作同口径通过结论。A_declared=4，实际依赖闭包未知，G-Q及AssetRegistry运行/物理/UE门未通过。当前硬record/JSON/raw/wire caps独立保留，不因度量差异放宽。

## I6 独立进程门

PR #85，final source `d8636d636d384355f94ecaaed76a64de9e10f610`，merge `3e02376d8b46d46f04d512ad88efa4808d36c665`。fresh非I1–I5作者；首run 19/20、日志路径撞symlink，整体失败完整保留。唯一修正run exact `140afc08e0dbcf05c2785ffdf3053b905c8cc563`：20cases、85真实child、12受控SIGKILL、0cleanup kill/error、全部reaped，输入hash不变，约5.64秒。W0–W9/RECOVERY_VALIDATED、实际replace/fsync、双writer/alias/inode/释放、坏历史拒读、未知重启幂等/预算cursor、只读及分段序列均独立磁盘观察，不调用prod validator当唯一判据。

原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I6-20261102-process-attempt1/raw-index.json` SHA `1adebb847047dcdd02c8b2cccc857effc1694f8c82641e64f6bf768febec0342`；attempt2同名SHA `e8d31b805728033ed0b9e1f4a20c8b7f0bbf3cee676d27b1ba136c00dc1d44da`。root复算949/956全部文件size/hash，逐83/85 exit核对真kill11/12、cleanup1/0且均reaped。之后仅保全旧output/symlink的guard+negative及文档，未第三次本地矩阵。root在finalsource独立复查两个拒绝路径，均实际FileExistsError且sentinel names/bytes/inode不变；原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I6-20261102-parent-output-review/index.json` SHA `9b5bff2458e8a525516f9b5b7e39cfcdcf687117c6e0655f204d2e828a7650a7`。最终CI verify成功（run41326147305/job124906382693），含新guard负例和全矩阵。

接受 **G-S1本地POSIX进程/同步故障有限门pass**；不证明断电、真实Genesis/UE、新0.2 blob/trust实现或跨设备。两卡均确认source为集成祖先且干净后清理worktree，分支/原件保留。

## 后继树与准入

共享v0.2变更按原U9允许的受影响局部卡实施，scope彼此独占：

- E1：codec/records/trust + codec/composite-record/trust tests；u7。G-C0.2/G-S1已满足。
- E2：ownership + ownership tests；u2。按冻结API并行编码，实际import/Check等E1准确PR合并，不复制stub。
- E3：Store + Store tests；等E1/E2接受，真实raw/descriptor/commit/recovery同步。
- E4：admission/commands/rules/physics protocols + commands/prepare tests；等E3，明确prepare/session及provider候选边界。
- E5：recovery + recovery tests；等E3，与E4并行。
- E6：非E1–E5作者独立0.2 blob/key/proof进程故障验收；等E4/E5。再解锁I8及I10对应真实接线。
- I9：固定新域严格UE parser三文件；u9，与E1/E2并行。G-B0/R-B仅parser实施+build/NullRHI准入，本卡不产生G-B1/I11或G-B2/I12结论。

E1/E2/I9统一baseline `3e02376d8b46d46f04d512ad88efa4808d36c665`。E1方案已root接受：生产代码内冻结allowlist，不依赖doc文件；key固定authority.key，partial NOT_READY不覆盖；shared context/protocol在codec，closure/BlobMeta/DTO在records。API补充open_trust(...,session:OwnerSession|None=None)，signing=True必须owner session，LocalTrust据此知道principal，不从hash反推；read-only verifier无需session，不给Store signer。schema/MAC/golden bytes不变。

实际R-B：UE5.8.3/CL58210709 `/Users/Shared/Epic Games/UE_5.8`，M4Pro48GiB，DevSSD余721GiB；发布时无真实UE/Reporter/worker。I9独占build/NullRHI总<=15min、raw<=256MiB；首build前再查真进程，保存实际PID/初始化/完整日志/exit；不启动Metal/PIE/Genesis、不改引擎，不全局清理。E1/E2各正式B-C单次<=120s，首batch+最多一次targeted、raw64MiB。
