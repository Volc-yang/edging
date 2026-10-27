# 混沌宇宙起源纵切契约（P0）

版本：`chaos-origin-contract-v0.1`
状态：**第一轮 PDCA 已接受的实验契约**（P0 PR #1，合并提交 `2659242`）。本文件定义本轮可实现接口，不宣称哲学映射、生态规律或生产架构已经定案。

## 1. 来源、目标与身份边界

用户确认的起点是“天地玄黄，宇宙洪荒”：城市、蛮荒、原野、森林、海洋、河泽已经共同组成近乎完美的混沌世界。第一轮只证明一个完整世界的 `CHAOS → ONE` 首次分化，且这一步可保存、重放、观察。空间呈现可用地形、网格、体积、水体或组合，不要求方块。

**已确认的语义：**玩家在世界内的化身属于世界之灵；现实操作者/账号与世界内身份必须分开。**本轮暂定：**tick 0 可有城市、居民与生物的可见表征，但只给场所稳定的**地理标识**，不将居民、建筑或场所先行提交为独立灵域。`ONE` 是世界整体之灵的首次可追踪边界，不是六类场所各自觉醒。后续是否给已有居民追认连续灵域、玩家化身何时取得独立灵域，留给下一轮契约决策。

“未知、随机、无主、无规律”在世界内表示秩序尚未可辨认或归属：场所存在，但其独立灵域法则与谱系尚未提交。运行时仍必须有唯一权威写者、可记录的生成种子和版本化的起源规则。首轮不把随机画面变化、UE 帧率或 Genesis 物理帧当成世界时间。

## 2. 权威与可见状态

| 对象 | tick 0 `CHAOS` | tick 1 `ONE` | 身份规则 |
| --- | --- | --- | --- |
| 世界 | 丰盛而连续的地理/文明/生态初态 | 同一世界和同一地理初态 | `world_id` 从初始化起稳定 |
| 六类场所 | 均已存在，可被定位/观察 | 保持原有地理标识 | `place_id` 是结构/地理标识，不等于灵域 ID |
| 世界整体之灵 | `null`，尚未提交独立边界 | 一个稳定 `world_spirit_id`，覆盖本轮样本区域 | ID 由世界身份与 seed 确定性派生；O1 不生成第二个世界 |
| 居民/玩家化身 | 可有非权威视觉表征；不提交独立灵域 | 本轮仍不提交个体灵域 | 现实操作者 ID 不进入世界权威状态；后续身份生成须有独立事件 |
| 因果事件 | 无 O1 事件；事件水位 0 | 恰好一个 O1 事件；事件水位 1 | 重复同一命令只返回原结果 |

本轮场景观感可比状态模型丰富。UE 的建筑网格、树模型、居民代理、灯光和天气表现可以重建；它们不自动形成新的权威身份，也不输入起源规则。世界形态与灵域状态通过同一固定 `world_id/tick/revision` 查询关联。

## 3. 版本、数值与规范编码

| 字段/规则 | 第一轮约定 |
| --- | --- |
| `schema_version` | `edgeworld.chaos-origin.v1`；未知版本拒绝读取 |
| `ruleset_version` | `chaos-o1-exp-v1`；只涵盖显式 O1 的实验规则 |
| `generator_version` | `chaos-geography-exp-v1`；D1 固定实现与参数 |
| `projection_version` | `chaos-ue-projection-exp-v1`；只约束可重建表现，不进权威状态哈希 |
| `protocol_version` | 沿用 JSONL v1 envelope，所有请求/响应携带 `request_id` |
| 逻辑时间 | `logical_tick=0` 为混沌初态；O1 只允许 `target_tick=1`。成功后 `state_revision=1`；本轮不再推进。 |
| 数值 | 世界 seed、tick、revision、水位与坐标均为 JSON 整数；绝对值不超过 `2^53-1`。世界坐标以厘米为单位；生成潜势用 `0..10000` 整数定点值。禁止 NaN/无穷与隐式浮点转型。 |
| ID | ASCII 非空字符串；`world_id`、`place_id`、`command_id` 分属不同域；不以显示名称作身份。 |
| 规范字节 | Worker 对权威状态/事件对象使用 UTF-8、JSON 对象键按字典序、无多余空格、有限整数、数组按契约顺序编码；SHA-256 小写十六进制。UE 只验证收到的版本/水位/摘要字段，不自行重新计算权威哈希。 |

第一轮只承诺**同机、同版本、同配置**的重建一致性。若后续追求跨语言/跨平台逐字节一致，应另立规范序列化 ADR；当前约定足够让 Python D1/D2 共享一个固定编码器。生成器不得依赖 Python 内建 `hash()`、全局 PRNG 状态或未记录的系统时间。固定 seed 和版本必须决定全部生成结果。`sha256-counter/v1` 抽样定义为 `SHA256(UTF8("edgeworld-chaos-rng-v1") || 0x00 || seed 的 8 字节大端无符号表示 || cursor 的 8 字节大端无符号表示 || UTF8(domain))`，取前 8 字节为大端无符号整数；每次抽样后 `cursor += 1`，`domain` 为生成器文档列出的固定 ASCII 标签。若 O1 日后消费抽样，事件须记录抽样版本、游标、值及摘要。本轮 O1 **不消费随机数**，随机游标前后相同。

`canonical(x)` 在第一轮定义为 Python `json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")` 的结果；所有键和枚举为 ASCII，显示名不进入权威字段。`initial_manifest_hash = SHA256(canonical(InitialWorld))`。`state_hash = SHA256(canonical({"world_id", "initial_manifest_hash", "logical_tick", "state_revision", "phase", "world_spirit_id", "event_watermark", "random_cursor"}))`，这里花括号列的是**固定键集合**，值取该 tick 已提交状态。事件头 tick 0 为 64 个 ASCII `0`；tick 1 的 `event_hash = SHA256(bytes.fromhex(previous_event_hash) || canonical(O1Event))`。D2 在持久 manifest 中保存以上输入和计算结果；UE 不重算这些摘要。

## 4. tick 0 初态清单

D1 输出一个规范、有限的 `InitialWorld` 对象。D2 将其作为不可变地理基线存入权威 manifest；UE/D3 可把同一清单作为静态投影输入。必要字段：

```text
world_id, world_seed, schema_version, generator_version, ruleset_version,
logical_tick=0, state_revision=0, phase="CHAOS",
random_stream={algorithm, version, cursor},
extent_cm=[min_x,min_y,max_x,max_y],
places=[Place...], watercourses=[Watercourse...], routes=[Route...],
world_spirit_id=null, event_watermark=0
```

`Place` 必须含 `place_id`、`kind`、`footprint_cm`（按固定绕向排列的闭合全局 XY 多边形，首尾点相同）、`elevation_cm`、`potential`。`kind` 只取 `city | wildland | plain | forest | ocean | river_marsh`，每种至少一个。`potential` 是气候/生态/文明等未来规则可使用的候选整数场，不表示该场所已有独立灵域。场所可相邻、嵌套或由过渡带连接，不要求一类一格；`footprint_cm` 必须在 `extent_cm` 内。重叠优先级和生成细节由 D1 文档声明；不能把 8×8 卦域索引写成混沌世界已经定案的自然法则。

`Watercourse` 至少含 `watercourse_id`、`polyline_cm`（全局 XY 点序列）、`marsh_place_id`、`outlet_place_id`；河道经过指定河泽并通向海洋，末端落入 `ocean` footprint。`Route` 至少含 `route_id`、`polyline_cm`、按路程顺序排列的 `place_ids`；验收路线覆盖城市、原野或森林、河泽、海洋，蛮荒在同一连续区域内可观察。几何/地形精度可近似，但不得在清单中虚报连通。世界初态的形态数据可由清单加版本化生成器重建；所有会影响未来演化的候选场必须进入权威清单或明确的内容寻址附件。

初始化时清单和 tick 0 状态须在同一可校验提交边界成为已提交事实。只有空状态目录可以初始化；若目录已有未知/损坏 manifest 或绑定到不同 `world_id/seed/schema`，必须报错，不能静默覆盖或创建新世界。

## 5. O1 状态转移与 JSONL v1

Worker 是单世界单写者；每次请求一行 JSON、每次响应一行 JSON。请求 envelope 为 `protocol_version, request_id, operation, world_id`，成功响应为 `protocol_version, request_id, ok:true, result`，失败响应为 `ok:false, error:{code,message,head?}`。本轮操作：`status`、`advance`、`observe`。不改变现有树或 Genesis worker 的操作语义；chaos worker 使用独立状态目录。

`advance` 的 O1 请求固定含：

```json
{"protocol_version":1,"request_id":"req-o1","operation":"advance","world_id":"chaos-demo","command_id":"origin-o1","expected_revision":0,"target_tick":1,"origin_action":"reveal_world_spirit"}
```

提交前检查当前为 `CHAOS/tick 0/revision 0`、`origin_action` 精确匹配、同一 `world_id`，然后产生 `ONE/tick 1/revision 1`。`world_spirit_id = "spirit-" + SHA256(canonical([schema_version, world_id, world_seed, ruleset_version])).hexdigest()[:16]`。O1 事件带 `event_id, cause_code="explicit_origin_reveal", command_id, logical_tick, ruleset_version, input_hash, before_state_hash, after_state_hash, previous_event_hash, random_cursor_before, random_cursor_after`；`event_id = "event-o1-" + SHA256(canonical([world_id, command_id, target_tick])).hexdigest()[:16]`。`input_hash` 是 `world_id, command_id, expected_revision, target_tick, origin_action` 这五个固定键组成对象的规范 SHA-256；`request_id` 只是传输相关 ID，不参与去重。同一次提交还保存完整 command 指纹和响应供去重。`event_watermark` 从 0 增至 1，`event_hash` 链入 O1；tick 0 事件头为 64 个十六进制零字符。

成功结果至少返回 `world_id, logical_tick, state_revision, phase, world_spirit_id, event_watermark, state_hash, event_hash`。同 `command_id` 与同一规范请求指纹再次提交，返回**首次持久化的结果**，即使当前已是 ONE；同 ID 不同指纹返回 `command_id_conflict`。新 command ID 在 ONE 再请求 O1 返回 `phase_conflict`；revision 不符返回 `revision_conflict`；`target_tick != 1` 返回 `invalid_target_tick`。这些失败均不改 manifest 或随机游标。

存储采用一个原子替换的权威 manifest，包住当前状态、tick 0/1 有限历史、事件链、command 去重结果与清单 hash。写候选临时文件、校验并 fsync，再原子替换并 fsync 目录；未尝试替换前失败返回 `persistence_failed` 并继续服务旧 head。一旦尝试替换后提交状态无法判定，返回 `commit_status_uncertain`，拒绝继续请求；重启校验磁盘上可见 manifest 后才能接受重试。与当前阶段 2 worker 的 fail-stop 原则一致。

## 6. 固定时间纯读观察

`observe` 必须指定已提交的 `logical_tick` 和 `view_spec.watermark`；本轮 `tick 0 ↔ watermark 0`、`tick 1 ↔ watermark 1`，不允许读取部分提交或用当前状态代替缺失历史。固定查询参数至少包括 `region`（本轮世界样本 ID）、`observer`、`resolution`、`error_budget`、`rules:{evolution,projection}`。其中 evolution 必须为清单的 `ruleset_version`，projection 必须是请求方声明且 Worker 支持的版本；首轮只支持 `chaos-ue-projection-exp-v1`。重复相同查询返回相同权威样本字节；观察不写状态、不消费随机流、不触发 Genesis，也不推进逻辑时间。

```json
{"protocol_version":1,"request_id":"req-look-0","operation":"observe","world_id":"chaos-demo","logical_tick":0,"view_spec":{"watermark":0,"region":"origin-sample","observer":"ue-camera-v1","resolution":"chaos-proxy-v1","error_budget":{"semantic_state":"exact","visual_geometry":"proxy"},"rules":{"evolution":"chaos-o1-exp-v1","projection":"chaos-ue-projection-exp-v1"}}}
```

结果至少含 `world_id, logical_tick, source_revision, watermark, phase, sample, projection_version, state_hash, event_hash, view_spec`。`sample` 固定含 `world_spirit_id`（CHAOS 为 JSON `null`）、`place_ids`、`watercourse_ids`、`route_ids`、`spirit_boundary_place_ids`（CHAOS 为空数组，ONE 为全部样本场所 ID 的稳定顺序）。UE 使用 `phase` 和边界列表决定视觉提示；这些提示可重建，不进入权威哈希。`sample` 不复制全部几何，几何按同一 `world_id/initial_manifest_hash` 从 D1 清单读取。结果必须包含 `initial_manifest_hash`，防止 UE 混用不同初态。

错误码至少包括 `world_mismatch`、`history_missing`、`watermark_mismatch`、`unsupported_rules`、`invalid_view_spec`、`corrupt_state`。错误水位必须拒绝，不退回当前值。`status` 返回同一当前 head 的 `world_id, logical_tick, state_revision, phase, event_watermark, state_hash, event_hash, initial_manifest_hash`，可用于 UE 启动与重启后确认。

## 7. 结构样例与独立交付边界

以下是 D1/D2/D3 共用的**最小规范 fixture**：`world_id=chaos-demo`、`world_seed=7`、六类场所、一条水路与一条观察路线。D1 可先以此做黄金样本，再扩展生成器；若需要改变字段或样本几何，先修订 P0 并通知 D2/D3。数值只是验证接口与连通性的实验数据，不代表最终世界地理或美术质量。

```json
{
  "schema_version":"edgeworld.chaos-origin.v1",
  "world_id":"chaos-demo",
  "world_seed":7,
  "generator_version":"chaos-geography-exp-v1",
  "ruleset_version":"chaos-o1-exp-v1",
  "logical_tick":0,
  "state_revision":0,
  "phase":"CHAOS",
  "random_stream":{"algorithm":"sha256-counter","version":1,"cursor":0},
  "extent_cm":[0,0,100000,100000],
  "places":[
    {"place_id":"city-1","kind":"city","footprint_cm":[[10000,10000],[20000,10000],[20000,20000],[10000,20000],[10000,10000]],"elevation_cm":200,"potential":{"civilization":8000}},
    {"place_id":"wildland-1","kind":"wildland","footprint_cm":[[5000,70000],[30000,70000],[30000,90000],[5000,90000],[5000,70000]],"elevation_cm":600,"potential":{"ecology":4000}},
    {"place_id":"plain-1","kind":"plain","footprint_cm":[[20000,10000],[50000,10000],[50000,30000],[20000,30000],[20000,10000]],"elevation_cm":150,"potential":{"ecology":6000}},
    {"place_id":"forest-1","kind":"forest","footprint_cm":[[30000,30000],[60000,30000],[60000,60000],[30000,60000],[30000,30000]],"elevation_cm":350,"potential":{"ecology":9000}},
    {"place_id":"river-marsh-1","kind":"river_marsh","footprint_cm":[[50000,30000],[70000,30000],[70000,50000],[50000,50000],[50000,30000]],"elevation_cm":50,"potential":{"wetness":9500}},
    {"place_id":"ocean-1","kind":"ocean","footprint_cm":[[70000,0],[100000,0],[100000,100000],[70000,100000],[70000,0]],"elevation_cm":0,"potential":{"wetness":10000}}
  ],
  "watercourses":[{"watercourse_id":"river-1","polyline_cm":[[40000,55000],[60000,40000],[80000,40000]],"marsh_place_id":"river-marsh-1","outlet_place_id":"ocean-1"}],
  "routes":[{"route_id":"origin-route-1","polyline_cm":[[15000,15000],[35000,20000],[45000,40000],[60000,40000],[80000,40000]],"place_ids":["city-1","plain-1","forest-1","river-marsh-1","ocean-1"]}],
  "world_spirit_id":null,
  "event_watermark":0
}
```

按第 3、5 节的规范编码计算，以上 fixture 的摘要与首个 O1 结果固定为：

| 项 | 值 |
| --- | --- |
| `initial_manifest_hash` | `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3` |
| `state_hash`，tick 0 | `e2030df396ae7f1f5c1466e475ac467d09daf397be52d3b983386402d88f3d0f` |
| `world_spirit_id`，tick 1 | `spirit-597eac36f6d6c494` |
| `state_hash`，tick 1 | `d6b6ec5b7543fe9dfa486708f4013425b4a63c9c734ec8da3720552c552cbb8c` |
| `event_id`，O1 | `event-o1-b90ad54f1ee75eeb` |
| `input_hash`，O1 | `562eace8a95c5f67b10fee4204b537cd53b5618c9985d98f3eb9e899a778e12a` |
| `event_hash`，tick 1 | `3b7a8899f219bde5207c2e754391b54c9212e56b04dece2b4acbb8aa4450548f` |

固定样本的 `status` 在初始化后应报告 `CHAOS/0/0/watermark 0`，执行上文 O1 命令后报告 `ONE/1/1/watermark 1`。`observe(0, watermark=0)` 的 `sample.world_spirit_id` 为 `null`、`spirit_boundary_place_ids=[]`；`observe(1, watermark=1)` 的 `sample.world_spirit_id` 为上表 ID，边界列表为 `city-1, wildland-1, plain-1, forest-1, river-marsh-1, ocean-1`。两次查询使用同一个 `initial_manifest_hash`，各自返回对应 tick 的 state/event hash。D2 在此基础上提交真实 JSONL 请求/响应 fixture；D4 只消费经过版本与水位校验的观察响应。

D1 owns generation and geometric validation, D2 owns O1/commit/worker, D3 owns static UE projection, D4 owns Observe-driven UE switching. They exchange the exact field names above; changing fields requires P0 revision and lead review. Existing Seed→Tree PIE files and state directories are outside this contract.

## 8. 阶段门与开放决策

P0 审阅门：主任务确认本契约能让 D1/D2/D3 在无重叠文件所有权的条件下并行；确认居民和玩家身份语义的“本轮暂定”范围；确认 O1 显式命令是技术验收入口。未审定前本文件只是一份提案。

后续 C1/C2 门：同 seed/版本初态摘要相同；O1 一次且可恢复，重复请求幂等；tick 0/1 固定水位 Observe 只读；UE5 真实 RHI 能看见完整初态和首次整体边界，并证明相机、帧率、暂停、显隐不改权威摘要。构建成功和示意截图不能替代这些证据。

未决的世界观与生产问题：`ONE` 的自然触发条件；居民既有生命与灵域追认的关系；玩家化身在 TWO/THREE/MANY 哪个阶段生成；“二”“三”的哲学/数学定义；城市社会、生态长期演化、能量守恒和跨平台确定性等级；完整宇宙规模与美术质量。这些不由本轮 O1 实验参数隐性决定。
