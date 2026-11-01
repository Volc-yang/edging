# I 实现轮统筹登记

状态：2026-11-02，v0.2，执行中。用户已明确同意[U9任务树](design/universe-integration-review.md)，要求分配subagents并实现；原U设计轮不重开。目标为I0–I12有界内核、新域Genesis/UE接线与独立组合验收，延期X分支不被默认为当前必需范围。

## Goal 与基线

现有goal“继续执行计划”仍为blocked且未结束；本轮显式调用create_goal被工具拒绝，原因是已有unfinished goal；当前API没有resume入口。没有将旧goal虚假complete或覆盖它。本轮继续按用户授权推进，以本登记保存里程碑，不宣称goal面板已active。

真实仓库 `/Users/yangacan/edgeWorld/edge-world`，集成分支 `codex/plan-consolidation`。启动基线 `b3e1fd4fac69ce7d78bf5c14a4d8ed554622048c`；主工作区 `feature/edge-world` 用户改动保留。仅依赖/契约/独立Check和资源门满足的卡可派发，后续每卡绑定届时准确输入SHA和独占worktree，不从移动基线各自猜接口。

## 节点、所有权与阶段门

| 卡 | owner / worktree / branch / base | 工作 / PR / 门 / 清理 |
| --- | --- | --- |
| I0 契约+可执行黄金fixture | `/root/u9_architecture_review`；`.worktrees/i0-universe-contract` / `codex/i0-universe-contract` / `b3e1fd4` | complete / PR #77 / source `2aabfcb`，merge `a9506eb` / G-C、G-S0契约pass / 干净且source为merge祖先，worktree已移除、分支保留 |
| I1 codec/records | `/root/u7_projection_design`；`.worktrees/i1-universe-codec` / `codex/i1-universe-codec` / `a9506eb` | complete / PR #78 source `ae4fd16`，merge `efba6fa` / 15tests、黄金/负例、非作者review和最终CI pass / 干净worktree已清理、分支保留 |
| I2 ownership/进程锁 | `/root/u9_architecture_review`；`.worktrees/i2-universe-ownership` / `codex/i2-universe-ownership` / `a9506eb` | complete / PR #79 source `232e0a7`，merge `d2b7d29` / 24tests、3.10grammar、最终CI、root review/raw8/8 pass；首轮漏归档/唯一attempt2补证如实保留 / 干净worktree已清理、分支保留 |
| I3 store/提交 | `/root/u9_architecture_review`；`.worktrees/i3-universe-store` / `codex/i3-universe-store` / `d2b7d29` | complete / PR #81 source `9a27207`，merge `69daec3` / 22tests+最终CI、root review/raw10/10及375/375 bytes pass / 干净worktree已清理、分支保留 |
| I4 commands/admission/rules | `/root/u2_physics_design`；`.worktrees/i4-universe-commands` / `codex/i4-universe-commands` / `69daec3` | complete / PR #83 source `5fcd8d3`，merge `607e550` / 17新+共78tests、CI/root review，首loader失败与唯一attempt2保留 / 干净worktree已清理、分支保留 |
| I5 recovery/observe | `/root/u9_architecture_review`；`.worktrees/i5-universe-recovery` / `codex/i5-universe-recovery` / `69daec3` | complete / PR #82 source `49f7b7a`，merge `09ed3bb` / 16tests+最终CI、root review/raw10/10及488/488 bytes pass / 干净worktree已清理、分支保留 |
| I6 无GPU独立故障验收 | fresh `/root/i6_fault_acceptance`；`.worktrees/i6-universe-faults` / `codex/i6-universe-faults` / `607e550` | complete / PR #85 source `d8636d6`，merge `3e02376` / 20cases、85child、12真kill及CI/review，G-S1有限pass / 干净worktree已清理 |
| I7 物理fixture/API契约 | `/root/u2_physics_design`；`.worktrees/i7-universe-physics-contract` / `codex/i7-universe-physics-contract` / `a9506eb` | complete / PR #80 source `e005c2c`，merge `fe2176a` / G-P0静态pass；G-C0.2未接受 / 干净worktree已清理、分支保留 |
| I8 真实Genesis新适配 | u2；原`.worktrees/i8-universe-genesis` / `codex/i8-universe-genesis` / `13899a2` | complete / PR95 finale4f12f4 / merge51b95de / 有限G-P1 pass、finalCI/root review；批准clean worktree清理 |
| I9 UE新域严格解析 | u9；原`.worktrees/i9-universe-ue-parser` / `codex/i9-universe-ue-parser` / `3e02376` | complete / PR #86 source `0a905cf`，merge `e47065a` / 最终Build与StrictV02 NullRHI真实exit0、finalCI/root review / 生成物归档后干净worktree已清理 |
| I10 单root worker/初态 | u9；I10A/ I10B独立branch/worktree | complete / PR96 mergedcfd3bc CPU，PR98 mergeb1c0371真实CLI/Genesis/propose/restart；root raw/CI接受 |
| I11 Host/启动接线 | u7；I11A原`.worktrees/i11-universe-host` / `codex/i11-universe-host` | partial / PR97 merge96466b5，全部构造/NullRHI及finalCI接受；真实LiveReadOnly入口/初始相机归I11B |
| I12 独立组合验收 | fresh i12；`.worktrees/i12-universe-acceptance` / `codex/i12-universe-acceptance` / `0a7a0fb` | I12A CPU准备complete/d6e30f7，未真实run；G-B2 planned，等I11B/R12与准确合并树 |

| I0E 共享契约局部重开 | `/root/u7_projection_design`；`.worktrees/i0e-universe-contract` / `codex/i0e-universe-contract` / `d2b7d29` | complete / PR #84 source `f13a73d`，merge `9ad01c3` / G-C0.2格式门pass（S_typed/G-Q不通过）/ 干净worktree已清理 |

| E1 codec/records/trust扩展 | u7；`.worktrees/e1-universe-codec-trust` / `codex/e1-universe-codec-trust` / `3e02376` | complete / PR #87 source `4a69788`，merge `3d6c161` / 116tests、finalCI、i6 review/root raw958 pass / 干净worktree已清理 |
| E2 ownership扩展 | u2；`.worktrees/e2-universe-ownership` / `codex/e2-universe-ownership` / `3e02376` | complete / PR #88 source `c3b02ad`，merge `accbe3b` / 首test alias错误保留，唯一12case重跑pass+finalCI/root review / 干净worktree已清理 |
| E3 Store扩展 | u2；`.worktrees/e3-universe-blob-store` / `codex/e3-universe-blob-store` / `accbe3b` | complete / PR #89 source `2f76b75`，merge `1f95fac` / 142tests、u7review、root raw12/12、CI pass / 干净worktree已清理 |
| E4 command/prepare/provider扩展 | u7；原`.worktrees/e4-universe-commands` / `codex/e4-universe-commands` / `1f95fac` | complete / PR #91 source `1fcae8b`，merge `a4c86b3` / 164tests、finalCI、独立review/root2321raw pass / 干净worktree已清理 |
| E5 recovery/proof builder扩展 | u2；原`.worktrees/e5-universe-recovery` / `codex/e5-universe-recovery` / `1f95fac` | complete / PR #90 source `0db45fe`，merge `33c4fcb` / 155tests、finalCI、独立review/root13raw pass / 干净worktree已清理 |
| E6 独立扩展验收 | i6；`.worktrees/e6-universe-blob-trust-faults` / `codex/e6-universe-blob-trust-faults` / `a4c86b3` | complete / PR #92 final `0ebd7b3`，merge `ba7568c` / 首15组+唯一segmented定向pass、89child/8kill全部回收，finalCI全suite成功、root原件/源码审查 / G-S1.2有限pass；干净worktree已清理 |
| E7 fixed support质量语义修订 | u7；`.worktrees/e7-universe-support-mass` / `codex/e7-universe-support-mass` / `13899a2` | complete / PR #94 final `be951dc`，merge `52dd964` / 17CPU+oracle、UE实际StrictV02/exit0与finalCI/root raw审查pass；首TArray测试失败保留 / 干净worktree已清理 |
| I0A 实际资产依赖审计 | u9；`.worktrees/i0a-universe-assets` / `codex/i0a-universe-assets` / `e47065a` | complete / PR #93 final `572d4a4`，merge `cb39e0d` / Build/NullRHI exit0、9content/4native/0gap、root111raw+9actual文件及DAG核对、finalCI pass；6生成物核验归档后干净worktree已清理 |

worktree均相对真实仓库固定`.worktrees/`；详细文件所有权、P/D/C/A与图见U9。I0已交付且只写 `doc/contracts/universe_authority_v0_1.md`、`doc/fixtures/universe_authority_v0_1/`、`scripts/validate_universe_authority_fixtures.py`。未提交输入不复制到子worktree；不得改旧S4领域/存档来迁就新schema。

## 已发布执行额度与审查分工

I0及本轮已发布I1/I2/I3/I4/I5/I6/I7/I0E各自正式获得本地stdlib无GPU检查额度：单次≤120秒、至多一次定向重跑、原件≤64MiB；不安装依赖、不运行UE/Genesis/模型，不写world状态。八份设计中候选75分钟/16GiB没有自动转为运行授权。

I0由`/root/u2_physics_design`准备非作者黄金bytes/hash复算与对抗审查；`/root/u7_projection_design`只读检查现Runtime envelope/UE兼容边界。这两项当前不是I1/I7提前实现。最终source经独立重算与主审接受G-C/G-S0（仅契约门），见[I0复核](design/universe-i0-coordination-review.md)。G-S1实际锁/故障/恢复仍planned。I1/I2/I7从同一merge `a9506eb7cadce9c5646e89f2c9daa48bf447730e`正式派发。I2编码可按冻结codec API并行，但实际import/Check边补充I1→I2，等待准确I1合并树；禁止stub。

采用code-complete-2的构造检查重点为Ch3需求/成功条件、Ch8边界验证、Ch12编码/单位/范围、Ch22行为正反验证，结合协作/范围检查；当前风险是新共享契约与持久化/并发接口，使用新domain与旧档隔离，保留原失败。已有用户授权覆盖本树实施和独立PR集成，不额外制造重复审批。

## 通用交付与收尾

每卡固定base/输入/独占文件、普通commit、独立PR到集成分支；owner自检、非作者审查、父级集成和真实阶段门分别记状态。黄金期望由独立算法/来源复算，不用同函数生成并验证自证。源提交/PR不等阶段门通过；未执行记planned，缺证inconclusive，真实失败保留并最小返工。

GPU/UE构建窗口按前置已满足的具体卡登记实际owner/环境/预算；测试只作用于隔离目录与精确进程，未知提交遵D_recovery/停写，不全局清理。每卡经审查/CI合入后确认干净且source为集成祖先才清理worktree，保留报告/分支/原件。阶段交付和最终收尾都更新backlog、精简上下文并commit/push；仍有活跃节点不称I轮或产品完成。

## 本轮接口补充（不改存档字节）

I1/I2共同采用 `ContractError(code: str, detail: str="")`，属性及长度约束沿I0；已同步两owner。此为已声明异常构造细节，不扩大schema。

I1额外接受纯 `records.validate_archive(archive, *, world_id, trusted_receipts)->ValidatedClosure`：严格验证五个archive keys/domain/version/test_profile后委托validate_closure；使包装错域/错版本负例由production入口拒绝，而非测试自写if。冻结bytes不变，既有调用不变。

I7物理参与者严格为1动态Sphere+1固定Box，两体；发布卡“两动态体+支撑”为统筹口误已撤回，不增加第三体。真实.gstraj不能塞fake候选/小JSON字符串；I7拟v0.2显式descriptor+raw blobs及局部模块API扩展，尚未冻结。G-C0.2/受影响局部实现和故障复验将作为I8/I9/I10前置，v0.1内核里程碑继续实施，禁止提前放行真实接线。

I3补充纯只读 `Store.world_id` 与防御副本 `Store.trusted_receipts`，供I5校验，不额外IO；fault context固定键为 `world_id,command_id,prior_manifest,new_manifest,object_digest,visibility_attempted`（不适用值null）。不改存档字节。

I3补充纯内存nonblocking操作锁与按Lease身份的活跃Store登记：同Store重入/并发mutator、同一live Lease第二active Store拒LOCKED；close注销但不关闭Lease，不得在操作中关闭后重新发布ready。无新线程/磁盘/存档字节；owner将在专属测试覆盖。

## 当前下一动作

E4/E5/I9已接受，准确source/merge、原始索引、最终CI及限制见[统筹复核](design/universe-e4-e5-i9-coordination-review.md)。当前集成代码HEAD `a4c86b382df01876a811af771df86af8a2fdb899`，不是主工作区或最终产品验收。

E6已独立接受，PR92 merge `ba7568c7742bbc989703f9449f96e06a89548e05`。首source057fcc2的15组通过，唯一失败为harness错误要求原子替换HEAD后inode相同；target source0db8769仅segmented通过，保留首失败；两轮89child/8真kill全部回收，原件17,003,816B。finalhead0ebd7b3 CI全suite成功（run41334290240/job124930716919），root完整review及两runner-index1860/178原件哈希核对通过。G-S1.2仅synthetic/localPOSIX进程/blob/trust门pass，不证明断电/Genesis/UE/敌对同UID隔离。见[E6报告](evidence/universe-E6/report.md)。干净已合并worktree已非force清理，分支/原件保留。

I0A PR93 merge `cb39e0df0138b6195b32e4e0f3ef5dced5d25cf8`接受安装版editor source-content资产图：9content/4native/352341B/0gap；root独立核对111raw及9实际UE文件、完整roots/Package edges/DAG/canonical；final572d4a4 CI run41334309759/job124930765837成功。见[I0A报告](evidence/universe-I0A/report.md)。只代表editor-source图，不是cook/许可/写实门；清理owner正在归档6生成物，DevSSD目标/branch/raw保留。

I8静态准备发现固定Box真实inertial mass默认0，而Python/oracle/UE要求所有mass>0。root与u2独立源码核实，局部重开E7技术语义：仅冻结fixed body-support允许实际非负值，dynamic仍>0；旧positive synthetic3200与golden/hash不改且不当真实读回。E7方案审查后实施/独立check，I8实际运行等其接受。批准未来I8预算内0step非对称pose/set_quat校准及初checkpoint恢复；p≤1e-6m、q±分量≤2e-6、norm²≤1e-6、零速度≤1e-6；dynamic解析质量rtol1e-6/atol1e-7kg为实验技术阈值，fixed runtime预期+0bits。未导入/运行Genesis。

### 当前正式派卡与清理交接

E7 owner u7，base `13899a2`，`.worktrees/e7-universe-support-mass` / `codex/e7-universe-support-mass`；已审定8路径（两契约、records、独立oracle、UE parser及测试、Python新mass测试、修订报告），仅fixed support mass≥0、dynamic>0，允许support±0且保留bits，原golden不改。CPU≤120s/raw16MiB、一次定向；额外R-B授权5min/raw128MiB的-NoUBA/紧凑NullRHI StrictV02及最多一次有理由定向。未将计划运行判通过。

I8 owner u2，base `13899a2`，`.worktrees/i8-universe-genesis` / `codex/i8-universe-genesis`；独占genesis_adapter.py、probe脚本、I8证据目录。已授编写/stdlib静态≤120s/raw64MiB，尚未授Genesis import/init/GPU；等E7接受后合并准确输入及正式GPU卡。已审bootstrap/frame/mass方案及真实身份冻结流程不得用fixtures替代。

I10 owner u9当前仅只读规划；无worktree/运行/实现，不猜I8未交接口。I11/I12后置。

I0A清理仅5个provenance一致链接和untracked DefaultInput.ini（SHA e1b7a60e4da1acca28b8540ed7b2746551df9ae1ddc0056eb45a0932ed82ea78），DevSSD链接目标保留。新cleanup raw-index SHA61b79d89e08088597344974b7aba0796d96c4e54971beffef0e238a423d5afb0，root核对13文件。路径 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I0A-20261102-cleanup-attempt1/`。source为集成祖先且worktree干净后非force移除，branch/raw保留。

后续完整树仍是I8真实Genesis→I10单root worker→I11显式Host→I12非作者真实组合验收，不能停在内核里程碑。

G-C0.2/G-S1有限门pass；S_records不等于S_typed，后者及G-Q仍开放。没有新域真实Genesis/UE组合通过证据，完整I树进行中。默认legacy、主工作区用户改动与网站路由保持原边界。

## E7接受与后继接口裁决（2026-11-02）

E7 final `be951dc80a4b11e2aed81512db0b8edcd9313d83` / PR94 / merge `52dd9646fd9871d164a30ba0c20bac3024845c85`。root逐差异审质量谓词、契约、闭包/proof边界；source1753680 CPU17tests+oracle67golden/57negative/5proof通过；首UE构建成功但新增测试TArray自别名断言保留，精确PID22352终止exit-9；唯一test-only fix source8601ad2 Build/StrictV02真实exit0，总149.45s。finalCI run41335504783/job124934361722成功，root核对CPU10/UE24+26原件。详见[E7记录](e7_support_mass_amendment.md)。6生成物核验归档后非force移除worktree；cleanup raw-index `e7004cf893058caa372010a4176f44a62b626d5e2fbc3441776207f6ee055173`，branch/raw/DevSSD输出目标保留。

I8 source834635c首次静态审计通过，root独立核对raw17/实际264源码/6 METADATA/adapter SHA；没有Genesis import。i6非作者预审提出两项最小返工：scratch不得落入authority；probe输入missing/unreadable/途中消失仍须保留原始异常、exit与index。u2获范围内返工、合并准确E7、stdlib定向与新build audit；adapter变化使旧B/O pins失效，旧原件保留，未授GPU。

I10只读规划三项裁决接受：

- 完整typed槽按明确分类/alias拟36，替换U8原32候选仅针对本technical profile；current typed≤288、S_records30与H≤64独立。资产、build/options身份和物理sample/snapshot/raw分账计件/bytes，不从总资源账消失。此profile只替换D/物理样本，typed槽不按+4增长；完整枚举方案待最终卡，不宣称G-Q通过。
- 可信launcher传canonical owner-config文件，0700目录/0600文件、nofollow/nlink1/ownerUID核对后读一次freeze；无key字节，无request路径/session变更，无动态import。默认existing/recover不开新root；显式owner初始化mode可注册空root，仍需initialize命令，status本身不初始化/求解。
- 真实B/O由外部正式bootstrap先审定，普通worker启动/status不得调用gs.init/measure_runtime_options；I0A实际资产body须重绑真实world并重算引用，I10纯组合单root。

I11由u7只读规划新Host/显式launcher，I10由u9只读规划；均尚未开始实现/运行，保持实际依赖门。

## 当前并行执行检查点

[执行依赖细化](design/universe-runtime-execution-refinement.md) @761a967：I10A/I11A固定接口CPU构造并行；I10B/I11B真实门仍等G-P1/I10B，I12独立组合后置。I10A base761a967 / `.worktrees/i10-universe-worker` / `codex/i10-universe-worker`；I11A同base / `.worktrees/i11-universe-host` / `codex/i11-universe-host`。二者已正式获CPU卡及独占文件，无真实Genesis或UE运行许可；I11的构建窗口另授。

I8修复source399bcd0，新build9243757d/adapter972f94首次真实options采集Oa91c16dc（4323B，GPU3.773s，23raw经root核对）。owner-freeze1仅真实外部key/publiccontext，authority路径未创建；随后物理attempt1在首Scene build后BUILD拒绝，0step、exit1/GPU4.642s，destroy/reap成功，23raw SHA5299d78b920a0a751e0f7b60449cd25ff8991d2f589774b4d986b6836b152cf2。

唯一0step诊断exit0/GPU4.217s，22raw index ac05d7a233f7b8e347bd5f860b08a03de74310ee4d283805fd875c6fd78f715c；root逐项核对actual/expected/source：material sdf_max_res128→32，rigid contact_resolution null→0、contact_patch null→false、impratio null→1、max_contacts请求cap32→实际candidate5、tolerance null→约1e-6。源码链完整，不由猜测判根因。G-P1未通过，无step/checkpoint/两臂证据。

root批准最小修复：bootstrap通过同参数public Scene.build零步后导完整5组actual+support material；_measure先实测B并全量重测当前owned scene O，无scene则零步identity scene导出/destroy；每次load/build后仍strict全量比较。config输入32及原goldens不改，不手抄派生默认，不跳字段。adapter变化需新B/O/context，旧原件仅历史失效输入。当前仅授代码/stdlib定向+新audit，GPU需新卡。R8已用A3.773s、B首4.642+诊断4.217=8.859s，失败均计600s/1GiB总账，不重置。

## 最新接受与下一真实入口

I8 PR95与I10A PR96已root独立review/finalCI/merge，见[I8/I10A统筹复核](design/universe-i8-i10a-coordination-review.md)。G-P1仅有限物理probe pass，真实world propose/单root CLI/UE组合尚未通过。前文失败/计划按原版本保留，当前有效B/O为post-build source9270349对应289d4f52/7165e3f0（实际world i8-physical-probe），旧pre-build pins不得用于新运行。

I10B下一任务从本精确合并树新建worktree，先固定采证driver/owner私有输入，再正式GPU卡验证真实CLI初始化/retain/weak/strong/幂等/历史/真实进程重访；新world wrapper要实际重新audit/零步测O、owner provision/pins，不把旧world记录直接拼接。I11R在原13路径内补被动trace与门控Exec采证接口/地理proxy，CPU先行，UE窗口未授。I12 fresh owner `/root/i12_universe_acceptance`只读计划已接受，等G-P1/I10B/I11B/R12；其新增driver路径已批准但未建worktree/未运行。

## 当前接受：I10B / I11A，下一I11B / I12

[I10B/I11A统筹复核](design/universe-i10b-i11a-coordination-review.md)为最新裁决。PR98 source/final15e0dc9/mergeb1c0371，真实CLI/propose/两正常worker恢复通过；PR97 final13498d7/merge96466b5，所有CPU/build/Protocol/Strict/TransportRaw通过，仅构造接受。原相对路径/compile/采证排序失败全部保留。I11B真实NullRHI existing入口与首次camera aim修正尚未执行；I12G-B2仍未执行。

I12A工具source a2b9fa2/final d6e30f7，纯stdlib verifier/被动driver/actionplan已交；首4/6、唯一2case targeted及新guard小卡2case通过，失败/源码区别保留。run仍硬拒绝，实际R12才授权dispatch，不把synthetic工具检查称组合接受。

## I11B入口重试与环境前置（最新）

I11B worktree `.worktrees/i11b-universe-live` / branch `codex/i11b-universe-live` / base c786b0b，3源码+I11B报告独占。source3ea2d07新增LiveReadOnly及首verifiedDTO一次camera LookAt；首build字符串拼接错误，唯一target sourceac9e430 build exit0但actualapp exit3：root批准的old owner inputs仍指向已移除I10B worktree，FileNotFound导致worker37513 normal exit1/reaped，未有首status；authority90/scratch6 maps与原owner SHA不变，总167.738s/180，原件保留。此为统筹清理漏迁移依赖，非通过门或状态损坏。

root已将原approved四输入逐SHA复制至DevSSD持久bundle `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I11B-20261102-persistent-owner-bundle/`，新owner-existing.json SHA5f0a46ca403423cb9a92a4d68dad92cde54d42fc81c33a6011278689273028f9；原owner/authority/key/context/session/scratch不变，无provision或solver，实际load_owner_config+load_inputs通过，publicpins仍ee04cf29a40cf1837a49967010af354836c79908034c83ba5106fd3f1b77ef67。新I11B-T卡90s/64MiB NoUBA+onlyLiveReadOnly已授，唯一新attempt3-persistent，仍待结果。后续配置输入须持久化并逐依赖检查，规则已补工作流。I11A旧6生成物清理原件index01b2a532a576b1092ff8e412adbada04552c285125b1277b64f093a1e77f2c8d共11文件root核验，旧tree非force清理、target/branch/raw保留；I10Bclean tree亦已清理。

I12A draftPR99最新tools sourceef17707 / evidencec14d4cd，PREP2修真实三参历史示例与action-before cursor/prefix/dev/inode marker等待；offline首因HEAD storage/archive profile混淆失败保留，改后只读真实I10B 81records/5roots/3raw及D/budget/cursor/steps全部吻合、所有maps不变。仅工具与离线子集，run仍禁用、G-B2 planned。

root CUA只读getState确认Mac locked，native自动解锁不能完成；已通过异步问题请用户手动解锁且无需启动UE/Play，等待回应。不得绕过锁屏/输入凭据。I11B NullRHI可继续；I12真实Metal可见阶段需解锁与最终准确合并树/R12实际卡，未开始运行或消耗其20min/2GiB候选。

## I11B接受 / I12执行器审查（最新）

PR100 final1d9f42f / merge36d88ec，经root准确源码、89原件、final CI及u9独立proof/资产/maps/退出复核，有限G-B1接受；[统筹复核](design/universe-i11b-coordination-review.md)。原始失败保留，I11B生成物归档/依赖检查交u7，待root非force清理。

I12 RUNNER code-only卡仍执行：精确root资源卡/产品source/显式execute后才允许监督器启动；默认不执行，父Popen实际wait，两个session聚合预算/逐阶段限制/DevSSD持久四输入与owner。root预审要求准确生成物allowlist，不能全拒实际必须的输出链接，也不能泛忽略untracked。产品必须选已集成PR97/100准确树；工具旧分支launcher不适用。未授实际UE/Genesis/新authority，G-B2未通过。fresh CUA仍锁屏，解锁问题pending。

I11B clean tree已root非force移除，branch/DevSSD/raw保留；cleanup11原件hash、42配置间接依赖检查、source祖先与clean通过，indexe73d86be7c7af0c2cadab97f0568347092a05776d6f13bdc1cf9e98dc596bec2。I12 runner独立u9预审要求两处局部返工：owner实际typedmetadata须与卡内四输入/world/root/mode交叉核对；日志IO错误不能阻断finally中的owned进程回收。旧检查/失败保留，实际R12仍未派卡。

I12A-RUNNER sourcea1170a4首8mock全pass（0.124s/raw1256B）；u9四项review后sourceb5a5851完成owner交叉、finally cleanup、liveENOENT与completion最终封存记账，唯一targeted5newcases全pass（0.120s/raw866B）。root源码复核和u9准确source复审接受工具准备，等待evidence-only final/PR99新head CI后集成；旧c14d4cd的CI不代表新source。初步receipt固定normal=false，existing只接受封存后completion。没有实际R12/G-B2通过。

## 当前可靠入口：I11B与I12A均已结算，I12B实际门等待解锁

- I11B PR100 final1d9f42f / merge36d88ec，有限G-B1接受；root与u9源码/raw/maps/proof/lifecycle独立review，finalCI成功。详见[复核](design/universe-i11b-coordination-review.md)。任务tree已非force移除，branch/DevSSD/raw保留。
- I12A PR99 finalb3902be36bf1d66db83ed0f2e2961725bfd4b580 / merge971ed03ea8f3de5db50ac386500325e14e4622ea。工具sourceb5a5851，后两commit仅证据；finalCI run41346566146/job124967537022 success。root复核35文件/215624B，indexfd1715289753f5633fa3f39e3ed9c0ff0c7adf2c87f9e792afcebf9dcfcfc1a3；u9准确source四fix复核通过。首8mock和唯一5case targeted通过，不冒称全suite重跑或实机通过。[报告](evidence/universe-I12/runner-report.md)、[资源卡接口](evidence/universe-I12/runner-contract.md)。
- I12A仅工具准备complete；clean/source祖先与42持久配置无间接引用确认后，root非force移除 `.worktrees/i12-universe-acceptance`，branch及全部证据已在集成tree保留。没有该工具的实际运行、UE/Genesis/新authority/keys或临时输出链接。
- fresh CUA listApps仍明确Mac locked，既有解锁问题pending；不尝试绕过或反复启动UE。I0–I12总树仍进行中，G-B2未通过，旧blocked goal未伪造恢复/完成。主工作区用户改动未触碰，远端feature合并不在本checkpoint内。

**下一轮第一步：**确认手动解锁；从准确已接受集成树获取新I12B实际验收worktree，载入本登记和runner contract。固定工具source与产品source（现产品集成971ed03，后续统筹文档提交不改产品字节），创建全新单authority/context/key和DevSSD持久四输入/两mode owner，真实来源预检后由root发具体R12卡，输出映射逐项allowlist。再按已接受P1做两个真实UE会话：显式初始化/retain/弱物理/幂等/历史写拒绝、各只读动作独立map、真实StartPlay/相机变换/Metal原图、正常退出与同root重访；root独立审查才裁决G-B2。候选总预算20min/2GiB尚未实际消耗，不把工具模拟与上游I10B离线数据算新实机证据。

## I12B恢复派卡（2026-11-02）

用户回复已解锁，root fresh CUA listApps确认native可用、UE/CrashReporter均未运行。I12B-PREP已派独立owner i12_universe_acceptance，worktree `.worktrees/i12b-universe-live` / branch `codex/i12b-universe-live` / basef854281。独占 `doc/evidence/universe-I12B/`（含准备helper），不改产品/runner/launcher；CPU120s/raw64MiB，仅持久部署、精确身份预检与新world可信owner配置，未授GS/UE/真实launcher。u9并行只读预审实际动作/相机读回/来源身份。root唯一UI协调，后续正式R12卡候选两session总1200s/2GiB（含build/所有失败），尚未消耗。已接受输入可在adapter/native/source逐项不漂移证明后提出复用同B/O字节，真实provider初始化仍测量；不得复用旧root或凭旧source拼新世界。UI截图/输入全经CUA，visible尽量fullscreen独立Space；正常退出与原始失败完整保留。

I12B预检补充：已批准真实B/O完整record含旧world_id，root/u9接受仅新world顶层元数据/O.buildref与digest重绑，body canonical保持一致，资产/audit同world重绑；原输入原件保留。u9独立复算accepted实际Gen264py/19critical/37native+METADATA及adapter15f5b96…abb192，均与当前安装一致；真实initialize仍_measure strict比较。

发现runner对真实venv Python symlink路径一律拒绝，故新增独立I12C-PYTHON叶：u7，`.worktrees/i12c-python-pin` / `codex/i12c-python-pin` / basef854281，仅runner及I12C证据目录。root/u9已审最小专用exact interpreter chain/targetSHA/同venv cfg与site身份pin；无pin保留旧拒绝、通用safe_path不变、原lexicalexe不替换、不造wrapper或改venv。stdlib120s/raw16MiB，first+一次定因targeted，无GS/UE。root实际启动清除PYTHONHOME/PYTHONPATH。两session runtime_files仅pin不可变安装文件，Host/plugin由每session实际build后二进制SHA另审，不能prepin将覆盖输出后换卡绕过。正式R12未派。

## I12B已具备实际启动条件（等待第二次解锁）

I12B-PREP PR101 final0d69fd9 / merge04c7693447f93c31253d4c313f7527aeb96f30e2，finalCI run41361753959/job125013393773成功（399tests/skip1）；root21公共原件/121948B与u9部署/source/typed配置独立复核通过，index43463c45…cb51a8a。I12C PR102 final2b92df5 / merge01b16d1ee940e8554a636a98e5e4718c4d65ae0e，source0c2e743首18定向+实际解释器链只读采集全过0.276s，无targeted；root10raw/11652B与u9独立源码审通过，index66ed82e9cbe24bcdefb3b150c74340daaf8198a760f18f56cc11a845ac989d2e；finalCI run41361811910/job125013569644成功。

实际product tasktree已ff到01b16d1，6精确输出allowlist保留。root已独占创建 `I12B-20261102-world/deployment/r12-root-approved-attempt1.json`，SHA72eb12762dc5ac04091bf3eeddfac5a3f0120c9a65dd48f8e3234669146bd3b8，完整initialize validate_run通过，未Popen。新world edgeworld-i12b-20261102；两slot800/400总1200s、2GiB，卡时效2h；source/四输入/owner/pins/完整Python链/不可变runtimefiles均固定，Host/plugin真实build后另取SHA。原candidate不改，authority/scratch仍absent。dispatchmetadata在持久prep/root-dispatch.json。

预检期间Mac再次自动锁屏，root freshCUA明确确认并已async请求再次解锁，不绕过锁。已启动临时 `/usr/bin/caffeinate -di -t 1800`（tool session68267）仅防后续idle display/sleep，不解锁、不改持久设置；结束时应关闭精确task进程或等有限时长到期。u9最终卡只读审、I12 owner后采证准备并行。用户解锁后root可直接启动固定card initialize supervisor，所有UI/截图仅CUA，运行期间productHEAD不改；不存在实际UE/Genesis/I12门通过。旧authority/主工作区/网站路由均未动。
