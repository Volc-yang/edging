# I7：Genesis 刚体支撑物理契约 v0.1

2026-11-01；parent=I；实施基线 `a9506eb7cadce9c5646e89f2c9daa48bf447730e`（I0 PR #77）。状态：**公开 API 静态核对与技术提案，待独立 G-P0 审查；G-C0.2 扩展未接受，G-P1 未执行**。依据 [U2](../design/universe-physics.md)、[U9 I7/I8](../design/universe-integration-review.md)、[kernel v0.1](universe_authority_v0_1.md)。只交付本文件和 fixture 目录，不修改 kernel、旧存档或 UE 引擎。

统筹已更正发布卡口误：**两个参与者=一个动态 Sphere 和一个固定有限 Box 支撑**，不是两动态体加支撑。Seed→Tree 仍是抽象初态的因果发展。几何、材料、刺激与发展 D 是有限工程实验，不批准物质/生命/灵域规律。

## 1. 固定输入与公开 API 审计

已安装发行版 METADATA 为 `genesis-world==1.4.3`，要求 Python `>=3.10,<3.14`。[source_audit.json](../fixtures/universe_physics_v0_1/source_audit.json)记录被只读解析的准确源码 SHA-256、定义行与包路径；**未 import genesis、gs.init、build、step 或运行任何 GPU**。安装包源码是版本依据，在线 `latest` 只作入口：[Scene](https://genesis-world.readthedocs.io/en/latest/api_reference/engine/scene.html)、[约定](https://genesis-world.readthedocs.io/en/latest/user_guide/configuration/conventions.html)。

| 公开能力 / 源码 | 本卡可确认的语义 | I8 仍需验证 |
| --- | --- | --- |
| `gs.init` / `__init__.py` | `backend=gs.metal, precision="32", seed=7`；Metal 不支持其64位精度选项 | 实际包/设备/精度日志；持久样本用 f64 容器不会把 float32 求解精度变成64位 |
| `gs.Scene(show_viewer=False, sim_options=..., rigid_options=...)`；`add_entity(...,name=...)` / `engine/scene.py` | 配置显式步进、命名实体；`SimOptions.dt` 为秒，每 step 内 `substeps` 单独定义 | 解析后的完整选项/默认值与包身份封存；新配置实际构建成功 |
| `gs.morphs.Sphere/Box(...,fixed=...)` / `options/morphs.py`；`gs.materials.Rigid` / `engine/materials/rigid.py` | 位置/尺寸米，quat wxyz；Rigid 的 rho 为 kg/m³、friction、needs_coup、gravity_compensation 可显式给定 | 质量 `get_links_mass()` 读回/几何一致；`coup_restitution` 是跨solver耦合参数，**不能冒充刚体反弹系数** |
| `entity.get_pos(relative=True)`, `get_quat(relative=True)`, `get_vel(relative=True)`, `get_ang()` / `rigid_entity.py` | 前三者读 authored base-link 原点；relative 不是“把向量转局部坐标”。get_vel 文档明确世界坐标及偏移输运项；get_ang 读取 world angular state 路径，quat 配合 wxyz 源定义 | 不对称基向量/已知姿态检查 frame、分量/轴向；不使用 DOF 数组当世界速度。记录 getter 形状/有限性和单位 |
| `get_contacts(with_entity=support,is_padded=False)` / `rigid_entity.py` | 最新 step 的实际接触，公开字段含 geom/link indices、world position、force_a/force_b；非并行 scene 为 live contact 行 | 用公开 `geom_start/end` 对应调用对，把 force_a/b 归一为作用于动态体的力；位置米、力 N 的接口/符号核对；不虚构 normal/penetration getter |
| `Scene.entities/entity_names/get_entity(name=...)` / `scene.py`；`Entity.name` | 公开稳定命名查找；名字会进入场景描述，默认自动名含运行期 UID | 恢复后恰两名字、角色/几何/材料/质量正确；不能用 `entities[0]` 冒认持久身份 |
| `rigid_solver.set_gravity`, `Scene.step(update_visualizer=False,refresh_visualizer=False)` | 刚体明确设置每 tick 重力；一步是 dt，不是 UE delta time | 每次加载后重新应用该 tick 输入，实际步数/配置相符；读取历史不调用它们 |
| `save_checkpoint(path)`、`Scene.load_checkpoint(path,show_viewer=False)` / `scene.py` | `.gstraj` 存场景描述及模拟数组，加载构建并恢复记录的场景 | 两体身份/状态读回及后续续算，不能从旧单球恢复推断已通过；字节 hash 一致性不等于跨运行文件必逐位相同 |

不访问 `_sim`、私有状态数组、任意未审计力接口；库内部实现的私有访问不是 adapter 的公共许可。上述源码只能证明定义/文档，不是可运行性或物理准确性证据。

## 2. 有界 fixture、单位与预声明 Check

[config.json](../fixtures/universe_physics_v0_1/config.json)是本契约的**精确配置模板**，所有非整数数值均为 kernel 同算法的 `$f64` big-endian bits。它不是从 Genesis 采得的结果。关键值：

- 单 scene、非并行环境，Metal precision32、seed7、`requires_grad=False`、无 viewer；`dt=0.01s,substeps=1,steps_per_advance=8`，每逻辑推进物理区间0.08s。
- Sphere：中心 `(0,0,1)m`、半径0.1m、非fixed，名称 `i7-dynamic`、PhysicalId `body-dynamic`、ExistenceId `existence-dynamic`。
- 支撑 Box：中心 `(0,0,-0.1)m`、完整尺寸 `(4,4,0.2)m`、fixed，上表面 z=0，名称 `i7-support`、PhysicalId `body-support`、ExistenceId `existence-support`。
- 两者 `Rigid(rho=1000,friction=0.5,needs_coup=False,gravity_compensation=0)`；禁止靠上下文默认密度猜质量。RigidOptions 显式固定碰撞、禁休眠/扭转/滚动/兼容模式等，准确字段见模板。其余解析默认值用同包公开配置导出封存；实际默认值漂移即换配置版本，不静默继续。
- `weak` 重力 `(0,0,-2)m/s²` 与 `strong` `(0,0,-9.81)m/s²` 为工程刺激，不称四相为真实宇宙重力法则。case_id 是该 tick 显式输入，指纹计入准确 config/binding/case。

所有位置/速度等通过公开 getter 拷贝到普通数值，再按实际 float32 值准确提升成 Python binary64 记录位型，**无精度升级声明**。位置/线速度是世界 SI，quat wxyz、角速度 rad/s。UE 显示的候选映射 `p_cm=100*S*p_m+origin_cm, v_cm_s=100*S*v_m_s, S=diag(1,-1,1)`、旋转 `R_ue=S*R_g*S^-1`、角速度按轴向量 `det(S)*S*omega`；变换仅由版本化 transform 记录声明，I8 验 getter frame，UE 后续另验实际呈现，不从 z-only 落体推断完整姿态正确。

每个新 tick：准确已提交 checkpoint→核对2名字/绑定→设本 tick gravity→8次 step→采样→checkpoint→发展函数。D 是动态体该 tick 的 `round_half_even((z_new-z_previous)*1000)`，先分别用 `Decimal.from_float(z_new)` 与 `Decimal.from_float(z_previous)` 精确转换原始有限double，再在 `localcontext(prec=2000,rounding=ROUND_HALF_EVEN)` 中做差、乘Decimal整数1000、以同一rounding的 `to_integral_value` 得安全整数；不是先做binary64差/乘法，也不使用默认28位Decimal；`|D|≤1000`。后态 `development_mm=D`，事件引用候选，UE 的抽象发展偏移从该字段生成；它不只是把原始物理轨迹另画一条线。D 是工程转移规则 `rigid-support-influence.v0.1`，非正式演化律。

预声明：两个隔离求解 attempt 从**同一初始 checkpoint 与同一其他配置/身份**出发，只有重力刺激不同，比较**第一次**8步的 D，要求 `D_strong < D_weak ≤ 0`。禁止预填旧 -7/-35 为本新支撑场景结果，禁止仅比较组合 hash/原始轨迹。后续每臂最多32次推进（256 physics steps），最后4个隔离候选/物理checkpoint样本须满足 Sphere bottom-to-support gap `[-0.005,0.01]m`、`|vz|≤0.05m/s`，且其间至少一次实际动态体—支撑接触；支撑位姿变化≤1e-6m。用 center.z−radius−box_top 计算 gap，不称它为引擎 penetration getter。

候选接收边界：位置分量 |p|≤10m，线速度≤100m/s，角速度≤100rad/s，接触力分量≤1e6N，quat norm²误差≤1e-4；样本恰2个、contact≤32、checkpoint每份≤8MiB。非有限、超限、错维度/单位/名字/配置/绑定直接拒绝；不截断/钳位伪造合法状态。这些是本实验技术门，待非作者审查后冻结，不能据此宣告写实真实性。

恢复 Check：在一次 arm 的固定 tick16 保存 checkpoint；新场景加载后，两体命名/配置/质量及 pose/速度的序列化 bits 要求与保存样本一致，随后8步与不中断对照的 pose/速度/D 一致（同机同包同设备/精度/输入）。raw checkpoint 文件可能带不同场景元数据，要求**每份自身字节 hash 可验证**，不强迫独立新建场景的两个文件整体字节相同。若不一致保留原件判 fail/inconclusive，不能事后放宽门；跨设备容差另立契约。

[static_vectors.json](../fixtures/universe_physics_v0_1/static_vectors.json)中的 -10/-40 只为 stdlib 舍入单元向量，标 `synthetic-stdlib-only-not-genesis-evidence`；它们不作为任何实时求解期望或 G-P1 证据。本目录没有生成/伪造 `.gstraj`。另列已缩放标量 ±0.5/±1.5 的 half-even检查；真实D输入路径用 ±62.5/±187.5mm ties（z=±0.0625/±0.1875）及 nextafter两侧检查。精确0.5/1.5mm对应的米差分母含5因子，不能由有限binary64的精确差构成，不能伪造这种输入；scaled-only向量不冒充Genesis采样。

## 3. 待重开 G-C 的精确 v0.2 扩展提案

**统筹已同意扩展方向供评审，未接受字段或 G-C0.2。**kernel v0.1 完全保留，I1/I2 可以继续独立实现/验证旧版；以下不能直接改它们的实现或把 fake 重命名为 Genesis。v0.2 是 authority schema 版本；物理 profile 名为 `genesis-rigid-support.v0.1`，两者版本域不同。

精确 envelope 仍为 `{domain,version,world_id,kind,id,body,refs}`，domain `edgeworld.universe.authority`，version 字符串 `0.2`。Canonical 算法/typed f64/IDs沿 kernel v0.1；新 record hash 为 `SHA256(b"edgeworld.universe.authority\x00v0.2\x00"+C(record))`，**与v0.1前缀不同**。不得混版本引用或用旧 hash 解释新 body。所有 kind 的 body/ref 精确字段见 [schema_proposal.json](../fixtures/universe_physics_v0_1/schema_proposal.json)；类型说明是契约，不是“允许任意扩充字段”。

`physics_config` body 精确等于 config.json 对象；`physics_binding.bindings` 恰2条，按 physical_id 排序，与 config.entities 的显式 index、name/role/ExistenceId 一一相符。名字是可重建查找键，物理ID才是持久引用；不为其他存在自动分配物理体或独立灵域。

`physics_sample.body.bodies` 恰2条、按 PhysicalId 排序，每条精确 `{physical_id,position_m:f64[3],quaternion_wxyz:f64[4],linear_velocity_m_s:f64[3],angular_velocity_rad_s:f64[3],mass_kg:f64}`；fixed support 同样读回，不凭配置抄结果。contacts 每条精确 `{pair:ID[2],position_m:f64[3],force_on_dynamic_n:f64[3]}`，pair 为排序后的两个 PhysicalId，力始终归一到 dynamic，按 `(pair,position_bits,force_bits)` 排序。仅接受从公开 pair-filter getter 得到的 live contact；raw global indices留诊断，不作持久身份。`physics_sample` 的 frame/precision 与 config匹配，refs 指同一 config/binding。

`checkpoint_descriptor` 指原始 `.gstraj` bytes 的 **SHA256(payload)，无 record prefix**、准确长度、格式/包版本及 config/binding。raw hash 仅能在该 kind 的 payload 字段解析，不能把任意64hex文本当文件路径。`physics_snapshot` 同时引用 sample、descriptor、config/binding与累计 physics_step_count；初态为0/case initial，成功 tick 增8。初态 state 指初始 snapshot，development_mm=null；后态 candidate 指前 state、新 snapshot/command，tick/rev按命令递增，后 state 与 candidate 同 snapshot 且 development_mm=D。

审批→最终指纹→物理候选→A→state→event→result/index→manifest 沿 I0 无环构建：v0.2 intent 增 config/binding 引用且以 case_id 取代中性 transfer；result.checkpoint 指 **physics_snapshot** 而非 fake candidate。manifest 闭包通过 state/event 覆盖真实物理 snapshot、descriptor与raw blob；只一个 HEAD，没有独立 physics head。genesis root没有event/index/prior_manifest；后续保留完整 prior链、精确 revision 水位、幂等/动作预算/随机游标。真实solver内部随机状态随checkpoint保存，不用观测或重试额外消费；kernel的实验游标仍仅已提交命令计数，不假称物理RNG状态。

建议上限：wire仍≤1MiB；每record≤64KiB、record字符串≤4096B、对象≤64键、record数组≤256、depth≤32；闭包最多2048records、归档JSON≤16MiB（顶层records包装单独计限），保留root≤64，含初态；每root恰引用一个snapshot/checkpoint，同一payload可共享存一次。每raw blob≤8MiB，全部保留闭包的**去重raw bytes**总≤512MiB（64×8MiB），没有给孤立/重复拷贝预留空间；孤立候选/失败原件/重复副本另进实际磁盘与I8证据账，预估超额即不准入新工作，禁止自动删除。这是新profile显式扩展，不能套用旧 archive≤256records/1MiB 的假定。record内部数组256与归档包装records数组2048用不同层级校验，不能把大包装送入record通用tree检查再悄悄放宽全部数组；wire≤1MiB另验。Wire不传raw binary；没有base64/超长字符串例外。所有真实尺寸还受本次采证更小资源预算约束。

### 存储与模块 API 的最小扩展（待统筹另发局部变更卡）

新增存储 profile `local-posix-blob-sync-v0.2`：保留 identity/稳定fd锁/JSON objects/唯一 HEAD；新增 `blobs/<rawSHA>.gstraj`。raw binary同样no-follow、nlink1、exclusive最终名、不覆盖，完整写+file fsync+blobs目录fsync **先于 V**；缺/坏/部分raw文件不能被HEAD引用，既有同名坏字节CORRUPT不静默修复。D仍同步authority根，D_recovery遍历并同步全部保留JSON/raw依赖及相应目录/HEAD；未知invalidate snapshot/fail-stop沿I0，不重新求解历史。

| 受影响模块 | 拟冻结的显式扩展输入/返回/错误 |
| --- | --- |
| I1 codec/records | 按version静态分派；增加上述精确kind及whole-closure关联校验。ValidatedClosure 增 `binary_refs:Mapping[rawSHA,BlobMeta]`；`BlobMeta` frozen字段 `sha256:str,byte_count:int,media_type:str`，media_type仅`application/x-genesis-gstraj;version=1.4.3`。v0.1返回空map；纯校验不读盘/不加载Genesis |
| I2 ownership | 拟定 `acquire(root:Path,world_id:str,*,initialize:bool=False,domain_version:str="0.1",profile:str="local-posix-sync-v0.1")->Lease`；新旧version/profile配对采用静态白名单，Lease增加冻结`.domain_version:str`。默认完全保留kernel0.1行为，选择0.2须显式传新profile；旧注册root不重标，错配ROOT_MISMATCH |
| I3 store | 新 frozen `BlobWrite {sha256:str,payload:bytes,media_type:str}`；CommitBundle 增`blobs:tuple[BlobWrite,...]=()`；`initialize(genesis:Sequence[Record],head:str,*,blobs:Sequence[BlobWrite]=())->CommitReceipt` 按初态闭包要求验证对应blob；v0.1必须空blobs。新增`read_blob(sha256:str)->bytes`只读已pin且通过闭包验证的blob，错/缺/坏为CORRUPT，非闭包引用REFERENCE。PinnedRoot增`blobs:Mapping[str,bytes]`；构建只读取得，不导入solver。Store重新验全部字节/hash/size与descriptor，先落稳blob后HEAD；fault增加`BLOB_FILE_SYNCED/BLOBS_DIR_SYNCED/RECOVERY_BLOBS_SYNCED`，上下文含raw hash，未知处理不变 |
| I4 commands/rules | 为v0.2显式注入 trusted `PhysicsProvider.propose(prior_state:Record,command:Record,intent:Record,*,records:Mapping[str,Record],read_blob:Callable[[str],bytes],ids:PhysicsIds)->PhysicsDraft`。PhysicsIds frozen字段 `candidate,sample,snapshot,checkpoint_descriptor`均ID；PhysicsDraft frozen `records:tuple[Record,...],candidate_digest:str,snapshot_digest:str,blob:BlobWrite`。provider只写受控scratch/返回候选，不打开authority root或提交。coordinator验F/来源，再A并唯一store.commit；v0.1仍用neutral_candidate，不动态导入不可信插件 |
| I5 recovery | 同lease全保留闭包验证，descriptor/raw size/hash验证与D_recovery覆盖raw；返回类型/未确认标签沿I0。加载当前Genesis属于I8/I10在storage ready后的显式操作；历史status/observe从已提交sample读取，无provider调用 |
| I8/I9/I10 | I8只实现provider与真实probe，不能自行持久写blob/HEAD；I9解析version0.2新sample/精确水位并拒fake/混版本；I10才经统一store组合worker。新错误增加PHYSICS_INVALID/PHYSICS_FAILED/BLOB_LIMIT（准确wire增补随G-C0.2冻结）；post-V仍传播StoreError，不把求解失败吞成成功 |

明确的provider生命周期提案：`GenesisProvider(config:Record,binding:Record,*,scratch:Path)`构造只保存校验后的输入，无求解/写盘；实际Genesis导入/scene初始化只在下列显式方法发生，模块import无副作用。

- `initialize(*,ids:PhysicsInitialIds)->PhysicsInitialDraft`：PhysicsInitialIds frozen `sample,snapshot,checkpoint_descriptor`均ID；PhysicsInitialDraft frozen `records:tuple[Record,...],snapshot_digest:str,blob:BlobWrite`，只建立物理初态及其工件；I10另组初态state/manifest，经扩展store.initialize唯一发布。
- `restore(snapshot:Record,*,records:Mapping[str,Record],read_blob:Callable[[str],bytes])->Mapping[str,JSON]`：加载准确checkpoint后重新采样，返回physics_sample的精确body键，不新建权威record、不写world；caller核对保存样本/绑定/配置。后续propose仍从传入已提交prior_state定位checkpoint，不从未提交内存续算。
- `propose(...)`采用上表冻结参数，IDs与当前world/profile核对，返回draft前验证全部样本和F；`close()->None`只释放自身scene资源，不修改authority目录或销毁证据。

新初始化入口的exact签名、raw闭包/故障hooks与profile配对均为**待接受的G-C0.2差异**，不是现行I0已有能力。非作者复核这些签名后由统筹另派局部实现卡，I8不得自行把blob塞进旁路目录。

### 与丰富混沌初态的差集

此v0.2提案仅含两个物理参与者与一个发展标量，**不含**六类地理/路线/水系、主体关系谱系、资产/投影清单或化身。I10需按U5另交精确typed起源schema、完整S/H/D/A/bytes枚举及组合fixture，经G-C相应版本合成审查后才放行；不能把本物理配置叫作丰富宇宙初态。复用唯一锁/HEAD/事务语义，不复用未批准世界律；任何扩展不原地改变kernel0.1或旧S4。

## 4. 未来运行门与资源准入

I8前置为 G-S1、独立G-P0、**G-C0.2扩展与受影响局部实现/故障复验**以及实际R-8 GPU窗口；本文件合并不自动满足这些门。候选窗口≤10min、raw≤1GiB、单arm≤90s进展窗口、最多2个物理刺激arm+一次checkpoint恢复续算；启动/Metal编译时间记录并纳预算，超预算停止新工作/保留原件，不强杀其他任务、不无限重跑。精确PID/环境/owner/起止与存储余量由统筹在派I8时冻结，不能借用U8 75min额度。

I8可在同一已归档初始checkpoint上串行创建隔离candidate scratch，分别固定weak/strong，不持久写新的world HEAD；每arm初态/每步/终态样本、checkpoint原件及其hash/尺寸、names/material/公共API输出、D复算和异常完整保留。它只产生有界物理/适配结果；I10/I12另证明真实物理进入唯一权威状态/事件与UE呈现，不拿独立probe充当世界集成。任一原始数据丢失/被覆盖，受影响Check inconclusive；失败/不一致不事后改期望。

负例至少覆盖：wrong world/config/binding、未知/重复名字、非法/超限/非有限结果、旧revision/错水位、fake混profile、checkpoint缺失/坏hash/超8MiB、save/load失败、恢复样本或后续D不一致、观察触发step、物理轨迹不同但发展D未变。求解/校验失败不更新world head；存储不确定由既有fail-stop恢复协议处理，不偷偷退旧状态。物理碰撞/容差与坐标实测均 planned。

## 5. PDCA 与实际检查边界

Plan：按更正的两参与者范围读取公开源码和上游契约。Do：交精确配置模板、静态source索引、synthetic舍入向量和v0.2/schema/API局部扩展提案。Check：本轮一次stdlib静态检查PASS（2参与者、11个D舍入向量、4个scaled向量、9源码+METADATA哈希、JSON未改，见fixture README与独立raw路径），不初始化solver、不给G-P1/真实物理/UE/存储耐久通过结论。Act：请统筹/非作者核对API与反事实可判性，裁决G-P0及G-C0.2扩展差集，另派受影响公共接口/故障卡；保留旧kernel并行实现和所有旧档。正式世界规律、写实/性能、跨平台仍开放。

Owner范围/格式检查：仅新增本contract与对应fixture目录；本地相对链接全部存在，`git diff --cached --check`通过。上述是已执行的静态Check，非作者G-P0审查、G-C0.2差异接受和全部真实运行门仍待进行。
