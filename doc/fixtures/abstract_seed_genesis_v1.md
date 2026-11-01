# G2-SCHEMA-FIXTURE：抽象 Seed→Tree × Genesis v1 工程输入

状态：2026-11-01，v0.1 **schema 提案，可做独立审查；物理反事实未实测，后续实现门未放行**。父节点 V-STG/G2-SCHEMA-FIXTURE，基线 `d3036e8`。seed 指可标识的抽象初态，tree 指累积的因果发展结构。本文的单 Sphere 是 Genesis API 工程探针，既不是植物种子，也不是已批准的世界物理法则。旧 `tree_worker.py` 与 `worker.py` 的领域存档及协议结果保持原样，新组合领域使用下述独立 schema。

## 1. 固定身份、求解配置与反事实输入

| 项 | v1 工程值与边界 |
| --- | --- |
| `world_id` | 两条反事实轨迹均为 `stg-demo`，分别使用全新、互不共享的 state directory；允许 ASCII `[A-Za-z0-9._-]`，1–64 字符 |
| 抽象初态/探针 ID | `seed_id="stg-demo:seed:0"`；`physical_probe_id="stg-demo:physical:0"`。两者属于不同身份域，不表示种子即刚体 |
| 因果节点/边 | 初态节点 `stg-demo:node:0`；每次成功 tick `t` 生成 `stg-demo:node:t` 与从 `t-1` 指向 `t` 的 `stg-demo:edge:t`；ID 与物理数值无关。这一技术纵切只有已实现的链，不证明真实宇宙必须是链或数学树 |
| Genesis | `genesis-world==1.4.3`、macOS Metal backend、单中性 Sphere（旧公开 API 路径：初始位置 `[0,0,1]`，半径 `0.1`）、`dt=0.01` 秒、`physical_steps=8`、`seed=7`；这些值只用于隔离探针，不推导世界尺度 |
| 两相刺激 | `phase="shaoyang"`（旧 adapter `gravity.z=-2.0`）与 `phase="taiyang"`（`gravity.z=-9.81`）；分别从同一初态的新目录推进一次，其余输入完全相同。当前 adapter 仅接受四相枚举；本卡不要求添加任意力 API |
| 反事实预期 | **预先声明**：在相同初态/设备/配置下，`influence_mm(taiyang) < influence_mm(shaoyang)`；不预填具体数值。若相同、倒序、缺样或无法重复，记录 `fail`/`inconclusive` 并修订 fixture，不能事后改阈值称通过 |

预声明请求序列分别见同目录 `phase_shaoyang.jsonl` 和 `phase_taiyang.jsonl`。两文件各在**不同的全新状态目录**运行，不能合并送入一个 worker。每条序列是 `status → observe(0) → advance(1) → observe(1)`；实施时再增加重复命令、负例与重启脚本，并保存原始响应。

当前进程调查：用户的 UnrealEditor PID `58296` 与 Chaos Worker PID `58437` 仍在运行；系统 `python3` 缺 `genesis`。本任务未启动第二 UE/Genesis Metal 进程，也未触碰用户状态目录。仓库根 `.venv-genesis/bin/python` 路径存在，静态导入回报 Genesis `1.4.3`；Metal backend 可用性与实际两相输出须在独占窗口核实。**本卡对两相真实输出和上述不等式的 Check 为 `inconclusive`。**

## 2. 数值与发展函数 F（仅工程探针）

求解器返回有限 IEEE-754 binary64 `position[3]` 和 `velocity[3|6]`。worker 在同一候选 tick 取 `z_new=position[2]` 与前一已提交物理状态 `z_previous`；使用 Python `decimal.Decimal.from_float(z_new)` 和 `Decimal.from_float(z_previous)` 精确转换二进制浮点值；在 `localcontext(prec=2000, rounding=ROUND_HALF_EVEN)` 内计算 `(z_new-z_previous)*1000` 并以 `to_integral_value(rounding=ROUND_HALF_EVEN)` 得到 `influence_mm`。记录实际 Python/Decimal 运行时版本，精确重演使用同版本。先分别验证原浮点有限，再运算；结果必须在 JSON 安全整数范围 `[-(2^53-1), +(2^53-1)]`，且本工程探针另限制在 `[-1000,+1000]` 毫米，否则以 `invalid_influence_range` 拒绝本 tick且不提交。精确半值向偶数整数舍入，例如 `2.5→2`、`3.5→4`、`-2.5→-2`。UE **只读取整数结果**，不重新计算 F。

每次成功 tick 的发展节点含 `{node_id,tick,influence_mm,physics_candidate_hash}`；因果边含 `{edge_id,from_node_id,to_node_id,command_id,physics_candidate_hash}`。`influence_mm` 必须由实际 Genesis 候选向量计算，并进入发展结构的 canonical hash；仅存物理 hash 或直接显示轨迹不算发展差异。规则 ID `abstract-causal-probe.v1`。反事实检查固定全部其他输入，仅改变显式 phase，比较同一节点 ID 的 `influence_mm` 与按第 4 节计算的 UE 抽象节点位置。此 F 不代表真实宇宙演化规律。

持久化的完整初态记录命名为 `seed_initial_record`，精确值为 `{"seed_id":"stg-demo:seed:0","seed_payload_schema":"abstract-seed.v1","seed_payload":{}}`；`initial_state_hash=SHA256(canonical(seed_initial_record))`。Observe 只投影紧凑的 `seed_identity={seed_id,initial_state_hash}`，不把它作为第二份权威初态。发展结构初态仅有 `{"node_id":"stg-demo:node:0","tick":0,"influence_mm":null,"physics_candidate_hash":null}`，`edges=[]`，`root_id="stg-demo:node:0"`。成功 tick 1 的 nodes 顺序为 node 0、node 1；node 1 具有上段的四字段。边精确为上述五字段，`from_node_id`/`to_node_id` 分别为 node 0/1。`structure_hash=SHA256(canonical({root_id,nodes,edges}))`；不得把物理候选单独追加为无关系的旁路节点。初始 `event_hash` 定为 64 个 ASCII `0` 字符，tick 0 无事件；初态物理样本来自 Genesis 新 scene 构建后的 `observe_body()`，其候选 hash 也须记录。

所有 JSON 整数字段（tick、revision、水位、`influence_mm`、步数）为精确整数，绝对值 ≤ `2^53-1`；tick/revision/水位非负。Python worker 使用 `json.dumps(...,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)` 形成 canonical UTF-8 字节并 SHA256。物理向量按求解器返回的有限 binary64 转 JSON 数字，hash 由权威 Python worker 计算；UE 不重算浮点 hash。恢复与重演对照限同机同包/设备/配置，跨设备容差另定。

## 3. 组合 JSONL v1 wire 字段

每条请求必需 `protocol_version:1`、非空 `request_id`（本连接内唯一）、`operation` 与 `world_id`。响应 envelope 必需 `protocol_version:1,request_id,ok`，成功时仅有 `result`，失败时仅有 `{error:{code,message}}`。客户端先核对 envelope，再按操作核对 result 身份；`request_id` 关联往返，`command_id` 关联持久幂等。

| 操作 | 请求领域字段 | 成功 `result` 必填字段 |
| --- | --- | --- |
| `status` | 无 | `world_id,schema_version="abstract-seed-genesis.v1",logical_tick,state_revision,seed_id,physical_probe_id,head_state_hash,event_head_hash,checkpoint_sha256,genesis_config_hash`；初态的 checkpoint hash 也必须可定位 |
| `advance` | `command_id` 非空；`expected_revision`、`target_tick` 安全非负整数；`external_inputs={"schema_version":"abstract-causal-input.v1","phase":"shaoyang"|"taiyang"}`；本版只允许恰好下一 tick | 同 status 的 head 字段，加 `command_id,record`；`record={logical_tick,state_revision,node_id,edge_id,influence_mm,physics_candidate_hash,checkpoint_sha256,state_hash,event_hash}`。重复同 command/payload 返回相同领域 result，响应 request ID 可不同 |
| `observe` | `logical_tick` 安全非负整数；`view_spec={watermark,region:"causal-fragment-v1",observer:"ue-causal-camera-v1",resolution:"causal-graph-proxy-v1",error_budget:{semantic_state:"exact",visual_geometry:"unmeasured-proxy"},rules:{evolution:"abstract-causal-probe.v1",projection:"causal-graph-ue.v1"}}` | `world_id,schema_version,logical_tick,source_revision,watermark,seed_identity,development_structure,physics_sample,state_hash,event_hash,checkpoint_sha256,projection_version,view_spec`。`seed_identity={seed_id,initial_state_hash}`；`development_structure={root_id,nodes,edges,structure_hash}`；`physics_sample={physical_probe_id,position,velocity,phase,physics_candidate_hash,genesis_config_hash}`。所有样本/引用来自同一提交 revision |

`observe` 的 `watermark` 必须等于该历史 tick 的 revision；本版每个成功命令恰好推进一 tick/revision，初态二者为 0。初态节点的 `influence_mm` 为 JSON `null`，edges 为空；之后 nodes/edges 按 tick 升序，既有节点不可被历史查询重写。`event_hash` 是该 tick 事件头，初态使用固定 genesis event hash；`checkpoint_sha256` 对应该 tick 的可加载物理前态/后态。UE 检查 world、tick、revision、水位、schema/投影版本、稳定 ID、节点/边引用完整性、物理候选引用、字段范围；错误或不完整响应不得更新画面或本地 head。

`command_fingerprint=SHA256(canonical({world_id,command_id,expected_revision,target_tick,external_inputs}))`，因此 phase/输入版本改变而复用 command ID 返回冲突。物理候选 hash 覆盖 `{physical_probe_id,position,velocity,genesis_config_hash,phase}`；事件 hash 覆盖前一事件 hash、命令、候选 hash、节点/边及 F 版本；状态 hash 覆盖 seed、发展结构、物理引用与 revision。准确 manifest/checkpoint 序列化实现由 G2-AUTHORITY 给出，不得放松单 manifest 提交点。

精确摘要输入：`physics_candidate_hash=SHA256(canonical({physical_probe_id,position,velocity,genesis_config_hash,phase}))`；`event_hash=SHA256(canonical({previous_event_hash,logical_tick,command_id,physics_candidate_hash,node_id,edge_id,influence_mm,rule_version:"abstract-causal-probe.v1"}))`；`state_hash=SHA256(canonical({world_id,logical_tick,state_revision,seed_initial_record,structure_hash,physics_candidate_hash,genesis_config_hash}))`。初态 `phase=null`、无边/事件，用完整 `seed_initial_record` 和初态物理候选 hash 计算初态 state hash；紧凑 `seed_identity` 仅用于 Observe，不参与 state hash，也不包含 state hash 自身。实现者不得把 `request_id`、UE 相机或墙钟加入这些摘要。

`genesis_config_hash=SHA256(canonical({genesis_version:"1.4.3",backend:"metal",dt:0.01,physical_steps:8,seed:7,initial_position:[0,0,1],radius:0.1}))`；phase 是逐命令输入，不包含在此固定配置 hash。`physics_sample.phase` 必填，初态为 JSON `null`，推进后回显命令 phase；其余字段在所有时刻必填。`nodes` 和 `edges` 的每个对象仅允许前述精确字段，不能擅自增加别名；若今后扩展，提升 schema_version。`record` 的 `node_id/edge_id` 必须指向该 revision 中的 nodes/edges。

## 4. UE v1 确定性纯投影

观察结果中的发展节点 `t` 映成一个 UE BasicShapes 代理中心 `(X,Y,Z)=(200*t,1*influence_mm,0)`，单位厘米；本探针 `influence_mm` 限于 `[-1000,+1000]`，因此 Y 位于 ±1000 cm；初态节点 `(0,0,0)`。每个因果边用中心间一条线段/圆柱表示，端点由两节点坐标确定，色彩按固定 `causal-graph-ue.v1` 材质参数表；物理样本可作为独立标记或文字证据，但不能替代发展节点差异。相同 Observe 样本须得到同样组件数、节点中心和边端点；相机与画质不参与投影输入或 worker 命令。这里的平面坐标只为可视化编码，不是 Genesis 世界坐标或最终宇宙空间。

v1 代理参数：每节点一个半径 12 cm 的球，初态线性 RGB `(0.0,0.6,1.0)`，成功 tick 节点 `(1.0,0.6,0.0)`；每边一个半径 2 cm 的圆柱，线性 RGB `(0.8,0.8,0.8)`，长度为两端球心欧氏距离，方向沿端点向量。投影不使用帧时间、相机位姿或未提交物理轨迹，组件以 node/edge ID 排序创建。屏幕可辨性仍须 Metal 实图独立验收，尺寸和色彩只是技术 fixture。

## 5. 错误与 Check

本组合领域冻结的 worker 错误码：`invalid_json`、`unsupported_protocol`、`invalid_request`、`world_not_found`、`unsupported_schema`、`invalid_command_id`、`command_id_conflict`、`revision_conflict`、`tick_sequence_error`、`invalid_external_inputs`、`unsupported_phase`、`history_missing`、`watermark_mismatch`、`unsupported_rules`、`unsupported_projection`、`genesis_failed`、`invalid_physics_result`、`invalid_influence_range`、`persistence_failed`、`commit_status_uncertain`、`worker_stopped`。UE transport/解析错误另记，不将其伪装成 worker wire code。负例、Genesis 失败、非有限值及缺历史不得产生成功提交；替换 manifest 已开始且结果不明时进入停止写入状态，重启后从磁盘判定。旧 worker 现有错误名与此新领域不必逐项相同。

**当前 Check：**请求/结果字段、ID 和 F/投影规则可静态审查；Genesis 公开 API 支持相位重力和 checkpoint 见 [旧 API 审计](../genesis_public_api_audit.md)及当前 `worker.py`。真实两相数值、checkpoint 可复查性、UE 解析和 Metal 画面均**未执行**；用户 UE/Worker 运行占用 GPU，且系统 Python 无 Genesis。阶段门为 `inconclusive`，G2-AUTHORITY/G2-UE 的并行实施仍待独立审查与隔离 Genesis 反事实短探针，不从文档存在推出运行通过。
