# U4：单权威事务、规则调度与恢复设计

版本：v0.1，2026-11-01；parent=U；状态 **proposed，待非作者审查**。固定基线 `3b5044debd8008eddbcc4c1fa85e45a8d43da217`；依赖 U1 `a7fed69`、U2 `b78b3ab`、U3 `9f2fe7e`；兼容 U6 `95903b2`、U7 `38f8e02`。本卡仅交付此文档，不冻结新 wire 或批准世界法则，不改产品、旧 schema、存档或 UE 引擎源码。

## Plan：输入、现状与有界目标

已定边界来自 [U1](universe-identity.md)、[U2](universe-physics.md)、[U3](universe-ai-proposals.md)、[U6](universe-entry.md)、[U7](universe-projection.md)及[第二批审查](universe-batch2-integration-review.md)：唯一权威提交；Genesis 与 AI 只提供候选/提案；UE5 发布版投影、相机、帧率与历史观察不推进世界；Seed→Tree 为抽象因果发展。万物有灵不预定独立灵域、演化规则、载具作用或其出现时刻。

**源码观察 @ 基线：**[组合 worker](../../engine/edgeworld_worker/abstract_causal_worker.py)有 `threading.Lock`、候选求解、不可变 checkpoint、manifest 临时文件/file fsync、replace 和目录 fsync；replace 已尝试后结果不确定即停写。它没有跨进程 writer lock，也没有本卡的通用规则图、身份、审批或预算事务。[旧故障测试](../../engine/edgeworld_worker/test_commit_boundary.py)针对旧 `worker.py` 的 replace 异常与**实际目录同步后再抛错**，不证明组合 worker、新设计或断电耐久性。未运行该测试或 Genesis。

本卡建议先收敛到**单机、一个声明的本地权威目录、单 writer、串行命令**；统筹通过只读 `diskutil info -plist /Volumes/DevSSD` 报告当前证据卷为 APFS，此环境观察不验证锁/fsync/断电保障；不支持网络文件系统、跨主机写入或跨服务分布式事务。不假设单次 rename 代表已耐久，也不承诺操作系统/磁盘失效后总能恢复；检测损坏必须显错停写。资源为一份主设计、至多两轮定向修订，不启动 UE/Genesis/GPU/模型，不下载依赖。

## Do：存储、锁与命名接口提案

### 1. 权威目录与锁

建议 world 绑定一个注册的 canonical authority root（先解析目录别名并核对目录 identity 与 WorldId）。启动可创建空目录，但须先取得该目录稳定 `.writer.lock` 文件的 OS 排他锁，才读取/初始化 manifest、加载 Genesis 或执行恢复。首个实现候选为 POSIX 本地文件描述符锁，例如 `flock(LOCK_EX|LOCK_NB)`；具体 OS/文件系统行为由实现探针验证，不能把当前 `threading.Lock` 算作已覆盖。

锁持有范围包括初始化、完整恢复校验、规则/Genesis 求解、blob/manifest 发布、回包和正常关闭；进程内再串行化请求。锁 fd 保持打开、close-on-exec，不传给子进程；正常关闭先停止受理/完成或停写在途事务，再卸载资源、释放 fd。异常进程死亡由 OS 释放锁，不按 PID、心跳超时或过期文本删锁夺权；**锁文件不 unlink/recreate**，避免不同 inode 的双锁。PID/时间仅诊断，不是锁凭据。恢复进程也必须先抢同一锁，失败明确 `writer_busy` 类拒绝，不替另一个 writer 修复存档。

软链接或不同拼写必须落到同一已注册目录/inode，开锁文件时拒绝被替换为符号链接；外部复制一份目录不获得原 WorldId 的第二权威资格，需明确备份/恢复或新分支世界登记。锁是协作协议，不防绕过协议的任意文件写入；发现 root/inode/锁身份变化即停写。未验证的 NFS/云同步目录不作为本地锁方案适用范围。

### 2. 候选逻辑记录与来源映射（非生产 wire）

| 来源 | U4 建议的统一引用及校验 | 提交/观察边界 |
| --- | --- | --- |
| U1 World/Existence/Relation | `HeadRef {world_id, logical_tick, state_revision, state_hash, event_head_hash, schema_version, rule_version, canonical_profile}` | tick 与 revision 独立；成功状态变更递增 revision，是否推进 tick 由命令契约决定。旧实验 tick=revision 仅在原 schema 内成立 |
| U2 binding/config | `binding_ref={version,content_hash}` 引用同 world/revision 的物理 ID→存在映射；`physics_config_ref` 引用 scene、形状/材料、设备/包、frame、步长/实际步数 | 运行时句柄/数组索引不作持久 ID；配置/绑定不匹配拒绝加载或候选 |
| U2 candidate/checkpoint | `physics_candidate_ref` 指含 base HeadRef、输入/配置/绑定 hash、带单位/frame 的有效样本；`checkpoint_ref` 是实际已封存字节的 hash/格式/包身份 | 两引用与发展结果/事件在同一 manifest root 发布；文件先存在不等于已提交候选 |
| U3 proposal/approval/budget | `proposal_ref, approval_ref, admission_receipt_ref, action_budget_transition_ref`；各含 scope/digest/policy 和来源 | 审批/admitted 不是世界事实；外部费用账簿与世界动作预算另域，见第 4 节 |
| U6 entry/command | `entry_intent_ref` 关联原始 scope、稳定 CommandId 与可查询结果；本地访问状态不入世界状态 | 会话 epoch 与 world 幂等键分开，重连不新建原命令；A 路径本地进入不隐式创建世界实体 |
| U7 ViewBinding | `unit_transform_version` 必须解析为 `TransformRef {version, content_hash, source_frame, target_frame, units, origin, supported_components}`；与物理 config frame 对照 | U2 提议的手性/米厘米映射由 U7 应用，U4只保存/校验版本关联；未核实旋转/接触分量不得以通用映射名掩盖。旧抽象图布局另用 projection version |

建议新 manifest root 指向不可变状态、事件链、历史索引、物理 checkpoint/配置/绑定、规则图/随机流后态、持久 command 结果和世界动作预算状态。`ruleset_version`（旧起源）与候选 `rule_version` 只通过显式 adapter/迁移描述对齐；不能直接改字段名、重算旧 hash。投影/资产/单位变换工件按历史版本保留，UE 的“本地投影事务”不是第二世界提交点。

### 3. Canonical、ID 与规则调度

**建议新 canonical profile，须后续 fixture 冻结准确字节：**UTF-8、排序对象键、无多余空白，解析前拒绝重复键/未知字段/不支持版本；整数为精确 JSON 安全整数，拒绝非有限数及隐式类型转换。凡需进 hash 的非整数物理量，建议使用有类型标记的有限 binary64 大端字节 hex 表示，记录 `float_encoding_version`，而不是依赖不同语言的数字打印；由 schema 区分普通字符串与数值字节，保留原始样本。新 profile 与既有 S4 Python canonical JSON **不能混用**；其精确旧字节/hash 原样保留。所有对象自 hash 字段从被 hash 内容排除，版本/域标签纳入 hash；数组顺序有语义的固定顺序，集合须按明确稳定 ID 排序。

命令指纹覆盖 world、可信 principal、命令类型/参数/目标、expected revision/目标逻辑时间、规则/输入版本和固定 proposal/approval/entry 引用；排除 request ID、重试墙钟、运行期 fd/句柄与传输字段。幂等键建议 `(world,principal,CommandId)`；同键同指纹返回持久结果，同键异内容冲突。提案/entry 已拒绝记录按原作用域保留于幂等操作账簿，同案同内容返回既有拒绝，修改内容使用新意图；账簿不可核实时不新发世界命令。服务先完成基本解析与结果读取授权，再查已提交结果，**在新动作的过期/head/预算重检之前返回原结果**；已过期不抹去已提交事实，未授权读取者也不能借 ID 猜取他人结果。

**摘要构建顺序（防自引用）：**①归档输出/提案得到 `proposal_digest`（排除自身摘要）；②构造待审批语义命令体 `B`，含动作/目标/参数/expected head/规则/提案引用，但不含 approval、admission、最终指纹或本次结果，得 `semantic_command_digest=H(B)`；③ ApprovalReceipt 绑定 `proposal_digest+semantic_command_digest` 与可信审批决定，得 `approval_digest`；④最终命令指纹 `command_fingerprint=H(B, immutable approval/proposal/entry refs)`，不再被反向放进步骤③；⑤物理/发展候选仅引用前态、最终命令和既定输入，候选发展 payload 排除本次 state/event/manifest hash 及自身 candidate digest，生成 `candidate_digest`；⑥最终准入 receipt A 绑定该指纹/候选及权限时间决定，不进入④的指纹；⑦发展状态 hash 覆盖状态/预算/随机后态与候选引用，排除当前事件头、command-result index 和 manifest hash；事件 payload 引用前事件 hash、最终指纹、审批/A、后状态 hash 和物理工件，排除自己的 event hash；⑧持久命令结果含 tick/revision、state/event/checkpoint 等稳定结果，不含新 manifest hash；去重索引指向该结果，最后 manifest 引用这些摘要。各自 hash 字段始终不参与自己的计算。`originating_event_id` 如需进状态，先由命令域+输出序号分配稳定 ID，与后算的 event hash 分开。禁止把 ApprovalReceipt 绑定的语义摘要误用为最终指纹，否则审批/指纹形成环；不得让结果/事件引用尚未算出的自身 manifest hash。以上是可无环构建的设计提案，具体字段/字节仍待 fixture 冻结。

U3 提案键 `(world,principal,ProposalId)` 稳定关联至多一个 CommandId，建议域分离 hash 派生，审批 receipt 变更不能悄悄换出第二命令。U6 本地 entry 请求在 `(world,principal,origin_session_epoch,entry_request_id)` 内去重；若 B 路径产生世界动作，稳定 CommandId 绑定**原始**进入意图，receipt 在重连后仍可查询。新 session/epoch 只改变回调/控制权，不改已发世界命令 ID；结果未知不凭重新打开窗口创建第二化身。ID 分配建议由命令域与输出序号确定，碰撞/已存在 ID 直接拒绝，不让候选失败耗掉不可追溯全局计数。

规则模块清单建议记录 `module_id/version, input/output schema, depends_on, trigger, read_set/write_set, conflict_policy, cost_bound`。注册先验 DAG 无环和版本依赖；同 tick 从准确已提交前态与显式输入确定触发集合，按拓扑层、再按稳定 module ID 排序执行。未来某模块输入依赖另一模块候选时必须有依赖边，不允许隐含全局可变状态。重叠 write_set 仅在批准的合并算子/优先规则下接受；否则冲突拒绝整命令，**不能用碰巧先执行者胜出**。求解可拆计算任务，但合并顺序/冲突处理确定，首版不并行写状态。

随机流是版本化输入：算法、seed、stream ID、起始游标或可复算域分离参数进命令/规则输入，按固定执行顺序分配消费，候选末游标随同一提交发布。失败不推进已提交游标；重试/恢复使用同输入，历史 Observe 不消费随机数。墙钟/模型输出若影响规则，先作为不可变 receipt/输出工件固定，不在重放期间读取当前时钟或重问模型。模块触发/冲突规则是工程接口，具体宇宙法则仍待批准。

### 4. 权限、审批与两种预算恢复域

实时受理与提交前重检由 writer 串行化：验证准确 head、当前可用 grant、审批 scope/digest/签发与撤销、deadline、目标范围和动作上限；Genesis/规则求解期间的准入不能替代最终重检。最后重检形成**提交准入线性化时点 A**，绑定完整候选/命令摘要、检查时刻和可信 policy/revocation 版本，其后在同一串行事务内立即封存并发布。A 前已生效的撤销/过期必须拒绝；已知将越过 deadline 的发布不放行。A 与实际 manifest replace 的间隔及失败均记录。

不能承诺外部审批服务在 A 后撤销与本地 rename “同时发生”：若要求撤销一直有效到发布点，须由权威内可串行化 policy 版本，或可核验的事务性准入凭证/服务协议实现；只靠两次 HTTP 读取不够。首个实现建议采用固定审批/可信输入 receipt，明确“A 后变更作用于后续命令”的候选语义；该语义未批准或外部服务无法给确定 receipt 时，不放行需要该保障的新动作，不能把竞态伪装为已实现的即时撤销。历史重放用 A 的原决定，不套用当前权限重判历史。

| 域 | 建议处理及未知状态策略 |
| --- | --- |
| 世界动作预算 | 可由 world 协调器管理的额度/消费与状态、command 结果在**同一 manifest root**提交；同 CommandId 结果只记一次消费。外部 quota 若是必要前提，先取得绑定命令的幂等 reservation receipt，提交中引用 receipt；跨域结算仍非原子 |
| 模型费用/生成账簿 | 不属于 world head，生成被拒绝仍可有费用。已归档输出与供应商 request ID/用量记录单独保留；重放/重试世界命令不再次调用模型。不承诺供应商计费 exactly-once 或请求取消即免费 |
| 审批/操作账簿 | 受理、拒绝、预留/释放/结算等按稳定意图 ID 幂等更新；本地日志/WAL 本身不代表世界提交。世界根可引用不可变已校验 receipt，但外部账簿更新不能成为另一个提交点 |
| 跨域未知 | 先按 CommandId 查询可验证 world root；若已提交，补齐外部幂等结算，不重做动作；确定未提交且外部明确状态后才释放预留。任一必要状态未知则冻结相关写入/预算范围并保留原意图，允许完整历史读取；不猜退费、不重扣、不用新命令重试 |

### 5. 发布、恢复与历史读取

候选顺序：持锁读/校验 head → 查幂等 → 准入与输入固定 → 依规则 DAG 求 Genesis/发展候选 → 全引用/有限值/规则不变量校验 → 最终重检 A → 写不可变工件 → 写 manifest 临时文件并 file fsync → atomic replace 唯一 manifest → authority directory fsync → 发布内存结果并回包。所有被新 root 引用的 blob 先 file fsync、原子落最终内容地址、同步其目录；新建目录还须同步父目录。manifest 与临时文件同文件系统，内容地址已存在须核对 hash/类型，不盲信同名文件。

**V=replace 成功的原子可见点；D=其后目录同步成功的确认点。**只在 D 后返回“已确认提交”；V 后/D 前结果未知时停止写入，不返回确定旧 head。进程存活时的 status/observe 不发布未确认候选；独立只读工具若直接读取磁盘新 manifest，必须标明 durability 未确认，不能替 writer 的确认响应。文件/目录 fsync 在目标 OS/盘上的实际保障（包括必要的 full-sync 能力）须单独验证；本设计不以 API 返回推出断电无损。

重启恢复先取得同一 writer 锁，从实际磁盘读唯一 manifest 一次并固定根：校验 schema/profile/world、状态/事件/命令与预算引用、**全部保留历史**及其 checkpoint/配置/绑定/投影版本；再加载最新 Genesis checkpoint 核对物体身份和状态，读取原 CommandId 结果。只接受完整旧 root 或完整新 root；任何被引用文件缺失/损坏、事件链或幂等结果不一致均拒绝服务并停写，不偷偷退旧备份、不补算历史、不重放模型求解来掩盖丢档。故障恢复/人工选择备份须另有明确记录与恢复契约。

**校验通过不等于耐久确认。**若先前可能中断于 V 后/D 前，恢复在同一 writer 锁内固定并校验可见完整 root 后，必须按已声明存储 profile 重新同步该 root 所依赖的必要 blob/文件目录及 manifest/authority 目录，建立新的 `D_recovery`；准确的依赖遍历、同步顺序及 OS/full-sync 保障由恢复 fixture 冻结。完成前不返回“已确认提交”、不受理新写，不因 hash 正确推断旧 D 成功；同步/保障未知则继续 fail-stop，最多提供明确标注 durability 未确认且不驱动求解的完整只读信息，损坏/缺引用时连完整只读也拒绝。`D_recovery` 不改逻辑状态或追加世界事件，只重新建立确认条件。D 后/W7 的磁盘新根同样先验证并在该恢复 profile 要求时重新确认，再从持久 CommandId 返回原结果；不能用新一次响应制造第二提交。

历史查询锁定一个已验证 manifest/root 与准确 `(world,tick,revision/watermark)`，解析对应不可变记录并返回同切片的状态、因果、物理与版本来源；tick 不唯一对应 revision 时须显式指定精确水位，不能挑最新近似值。缺历史或错水位拒绝；Observe 不加载求解器来重建过去、不消费规则/随机/模型、不写 receipt/head。初期不做自动 GC；未来 GC 必须持锁、追踪全部保留 root/读者 pin 和备份，绝不删活跃/历史引用。原子替换后的旧 fd/root 仍可供已 pin 的纯读结束。

离线结算建议先显式请求有步数/时间/资源上限的逐逻辑步推进，逐步应用规则、每步同样提交且有可恢复进度。预算耗尽可停在最后完整已提交步，不声称整批回滚；批次 ID 与每步 CommandId 确定，重试查原结果。大步积分、休眠近似和无人在场自动时间推进另立等价/误差契约，不能假定与逐步演化等价，更不能按 UE 帧率补账。

schema/rule 升级作为显式迁移计划：固定旧根和版本/转换器 hash、核对可加载性、离线生成新候选/验证，再用专用迁移 CommandId 发布新 revision（tick 是否改变由迁移契约规定）。保留旧档原字节/hash与历史解释器/工件，不篡改旧事件；不可逆或旧 runtime 不可用先停在只读，不原地重标 S4 为生产世界。迁移有旧/新 canonical profile 桥接记录，旧幂等结果保持可查询；版本不支持显式拒绝。

## Check：写点与崩溃窗口矩阵

以下全部为未来 **planned** 故障注入，不是已运行结果。先固定本地 OS/文件系统/存储、准确代码/fixture/profile、注入点和原件目录。每一行保存 head/事件/command/预算/随机游标、全引用 hash、实际进程退出与恢复日志；独立 checker 验证旧/新根及拒绝路径，区分进程 kill、系统 crash 和真实断电，不能互相替代。

| 写点 / 中断窗口 | 应有恢复/返回 | 失败信号 |
| --- | --- | --- |
| W0 建目录/开锁/诊断元数据 | 无 manifest 时仍是未初始化；另一 writer 拒绝；初始化 blob/新根按同样协议发布 | 半初始化被看作空新世界；删锁/换 inode 后双 writer |
| W1 外部预留/准入 receipt 写入或回包丢失 | world 仍旧根；按稳定意图查询外部状态，未知则冻结，不生成第二预留 | 未知被当失败而重扣/退回，或 admitted 被当 committed |
| W2 Genesis/规则候选与临时文件写入 | 无新 root，旧随机游标/预算/事件不变；重载已提交物理，必要时停写 | 失败后内存候选继续被下一命令使用 |
| W3 blob file fsync/内容地址 rename/目录 fsync | 未到 V 时旧根；可能有孤立文件，不能观察为已提交；任意引用已有文件必须完整可校验 | 尚未落稳或损坏 blob 已被新 root 引用 |
| W4 manifest temp 写/flush/file fsync | 未到 replace，旧根；临时文件不能自动当新 head；重试仍查原命令 | 打开半写临时 manifest 继续服务 |
| W5 replace 已尝试/返回异常或 V 后崩溃 | `commit_status_uncertain` 类结果并停写；重启持锁校验磁盘完整旧/新根并重建 D_recovery 后才确认/写入 | 根据内存旧 head 断言没提交、继续写或重复执行 |
| W6 V 后 authority directory fsync 失败/回包未知 | 同上不确定；校验完整根仍不等于耐久确认，须 D_recovery；同步未知继续停写/标未确认只读 | 把 LogExit、rename成功或后抛同步错误当断电耐久证明 |
| W7 D 后、内存发布/响应前崩溃 | 磁盘新根含 CommandId 结果/事件/预算；恢复验证并按 profile 建立 D_recovery 后同内容重试返回原结果，无新物理步/事件 | 响应丢失造成二次提交或已过期否认既有提交 |
| W8 world 新根后外部结算前崩溃 | 查世界结果，幂等补结算；外部未知冻结相应新动作，世界历史仍可读 | 结算失败回滚世界、重跑模型或再次消费世界预算 |
| W9 关闭/清理或迁移时崩溃 | 未确认事务按前述恢复；锁随进程死亡释放；旧/新迁移根均带版本和完整工件 | 清临时/GC删保留历史，或旧 schema 被静默重解释 |

| 行为正反例 | 固定示例与预期 | 可判失败 |
| --- | --- | --- |
| P1 正常+响应丢失 | W 的 `(tick4,rev7)` 经 C1 产生按契约允许的下一 tick/rev8、事件与物理/发展同根；W7 崩溃后同 C1 查询 | 先校验完整根并完成适用的 D_recovery，只一条世界消费/事件，返回原稳定结果；校验即冒认已确认或两提交均失败 |
| N1 双 writer/别名 | 进程 A 从初始化持续持锁；B 经 canonical root 和别名打开同世界，并尝试恢复 | B 拒绝；按 PID/超时删锁或另造初始化即失败 |
| N2 悬空/坏历史 | 新 root 指向不存在 checkpoint；另删/损坏一个保留历史工件 | 恢复/查询拒绝且停写，不用当前物理状态填历史；偷补算/静默回滚即失败 |
| N3 scope/水位/重复冲突 | 错 world、旧 revision、错误 watermark、同 C1 异参数/approval receipt | 拒绝，已提交 root 不变；旧案自动重基或新审批变出第二命令即失败 |
| N4 权限/期限/账簿 | 求解中撤销/到期，A 前可见；另在外部预算回包时断线 | 前者最终重检拒绝；后者冻结/核对，不重扣或猜释放。A 后外部语义无协议却称即时撤销即失败 |
| N5 规则/随机/离线 | DAG循环、未定义冲突合并、模块隐藏随机；离线第k步中断重试 | 前者拒绝；后者从最后完整步查结果续算，游标不重复消费。跳步冒充逐步等价即失败 |
| P2 历史/观察 | 同根精确水位重复 Observe、UE换视角/LOD/历史 | 全权威文件集合/hash、事件、预算和随机游标不变，不求解；只看route首尾hash代替逐项检查不接受 |

## Act 与当前 PDCA 结果

- **Plan：**以已接受的 U1/U2/U3 为依赖，兼容 U6/U7；单机本地盘、单 writer、无分布式原子性承诺，数值/存储/审批语义须后续冻结。
- **Do：**仅此文档交付锁、命名映射、canonical/幂等、规则/随机、两预算域、发布/恢复/历史、迁移及离线边界和故障矩阵。无 UE 源码改造需求。
- **Check：**本卡做只读源码与固定输入审阅、字段/所有权/故障窗口人工核对；文档范围、相对链接、差异格式在最终提交前执行并记实际结果。未启动引擎/求解器、未注入故障，所有新运行门 planned。
- **Act：**请非作者复核锁全生命周期、A/V/D时点、外部恢复域和完整历史；接受本卡只解锁 U8/U9 设计。实施先拆无 GPU 的存储/幂等/锁故障 fixture，再按批准物理/审批/负载契约放行适配与真实集成，不预定世界演化规律。

**Owner 实际检查：**8/8 本地相对链接存在；W0–W9 十个写点各列一次并有恢复预期与失败信号；定向修订后复核 V/D 未知窗口须 D_recovery，验证完整性不冒充耐久确认；人工核对 A/V/D 时点、摘要构建无自引用、幂等/预算恢复域和历史不求解；单文件范围与 `git diff --check` 通过。独立设计审查、新 wire 冻结、OS/磁盘保障、权限/期限和跨域预算协议以及全部新运行门仍 planned。
