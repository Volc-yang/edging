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
| I8 真实Genesis新适配 | 等I6/I7/G-S1/G-P0/R-8 | queued / 未建 / G-P1 planned / 未建worktree |
| I9 UE新域严格解析 | u9；原`.worktrees/i9-universe-ue-parser` / `codex/i9-universe-ue-parser` / `3e02376` | complete / PR #86 source `0a905cf`，merge `e47065a` / 最终Build与StrictV02 NullRHI真实exit0、finalCI/root review / 生成物归档后干净worktree已清理 |
| I10 单root worker/初态 | 等I6/I8/G-S1/G-P1 | queued / 未建 / planned / 未建worktree |
| I11 Host/启动接线 | 等I9/I10/G-B0/R-B | queued / 未建 / G-B1 planned / 未建worktree |
| I12 独立组合验收 | 非相关实现owner，待I10/I11/G-P1/G-B1/R-12 | queued / 未建 / G-B2 planned / 未建worktree |

| I0E 共享契约局部重开 | `/root/u7_projection_design`；`.worktrees/i0e-universe-contract` / `codex/i0e-universe-contract` / `d2b7d29` | complete / PR #84 source `f13a73d`，merge `9ad01c3` / G-C0.2格式门pass（S_typed/G-Q不通过）/ 干净worktree已清理 |

| E1 codec/records/trust扩展 | u7；`.worktrees/e1-universe-codec-trust` / `codex/e1-universe-codec-trust` / `3e02376` | complete / PR #87 source `4a69788`，merge `3d6c161` / 116tests、finalCI、i6 review/root raw958 pass / 干净worktree已清理 |
| E2 ownership扩展 | u2；`.worktrees/e2-universe-ownership` / `codex/e2-universe-ownership` / `3e02376` | complete / PR #88 source `c3b02ad`，merge `accbe3b` / 首test alias错误保留，唯一12case重跑pass+finalCI/root review / 干净worktree已清理 |
| E3 Store扩展 | u2；`.worktrees/e3-universe-blob-store` / `codex/e3-universe-blob-store` / `accbe3b` | complete / PR #89 source `2f76b75`，merge `1f95fac` / 142tests、u7review、root raw12/12、CI pass / 干净worktree已清理 |
| E4 command/prepare/provider扩展 | u7；原`.worktrees/e4-universe-commands` / `codex/e4-universe-commands` / `1f95fac` | complete / PR #91 source `1fcae8b`，merge `a4c86b3` / 164tests、finalCI、独立review/root2321raw pass / 干净worktree已清理 |
| E5 recovery/proof builder扩展 | u2；原`.worktrees/e5-universe-recovery` / `codex/e5-universe-recovery` / `1f95fac` | complete / PR #90 source `0db45fe`，merge `33c4fcb` / 155tests、finalCI、独立review/root13raw pass / 干净worktree已清理 |
| E6 独立扩展验收 | i6；`.worktrees/e6-universe-blob-trust-faults` / `codex/e6-universe-blob-trust-faults` / `a4c86b3` | complete / PR #92 final `0ebd7b3`，merge `ba7568c` / 首15组+唯一segmented定向pass、89child/8kill全部回收，finalCI全suite成功、root原件/源码审查 / G-S1.2有限pass；干净worktree已清理 |
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
