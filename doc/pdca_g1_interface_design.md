# G1-INTERFACE：4D 世界纵切接口设计

状态：2026-11-01，v0.2 **设计提案**。输入基线 `29facac`；依据 [G1 独立审查](pdca_g1_interface_review.md)修订，尚未经本版独立审查。本文件只界定下一版本的开发接口和验证方法，不批准玩法、物理参数、植物规律、AI 模型或产品验收阈值。

## 输入事实与待冻结决定

- [阶段 1 原型契约](phase1_4d_prototype_contract.md)规定 worker 单写者，Genesis 返回候选物理结果，UE 只提交显式命令并观察已提交状态。原型为单世界、单刚体、单机。
- [Seed→Tree 契约](seed_tree_4d_render_slice_contract.md)复用 JSONL v1 envelope：`protocol_version`、`request_id`、`operation`、`world_id`，响应为 `ok/result` 或 `ok:false/error`。树 Worker 与 Genesis Worker 分离。
- [G0 提案](pdca_g0_version_goal_proposal.md)的第 4 节产品范围、平台、性能/视觉/可靠性阈值尚未冻结。AI 和 Genesis 是否进入下一版必要纵切也未裁决。
- 现存 `engine/edgeworld_worker/worker.py`、`tree_worker.py` 和 `engine/chaos/origin_worker.py` 有各自领域语义。共同 envelope 不等于共同状态 schema 或可互换的错误集合；本设计不要求把它们并成一个运行时。

**G0 需先裁决：**本版本固定场景与成功信号；AI/Genesis 是必需、可选还是排除；目标机器、规模、预算；有效视觉/性能/恢复门。裁决记录应给出版本号和 owner。G1 可以做接口设计与探针，依赖这些决定的产品实施和验收继续等待。

## 职责与版本边界

| 边界 | 唯一写入者与输入 | 输出/只读者 | 失败与禁止路径 |
| --- | --- | --- | --- |
| 4D 权威层 G2a | worker 接受显式 `advance`，以 `world_id`、`command_id`、`expected_revision`、`target_tick` 和版本化规则输入形成候选状态；提交状态、事件、去重记录 | `status` 和 `observe` 返回已提交的 revision、tick、水位、稳定实体 ID、状态/事件摘要与呈现样本 | 冲突 revision、重复 ID 不同负载、缺历史、损坏状态须显式错误；渲染帧/查询不写入 |
| Genesis 适配 G2b | 仅由权威 worker 在候选 tick 调用，输入固定求解器版本、设备、单位、步长、子步数、场景和前态 | 返回候选轨迹/状态及诊断，供权威层验证后提交 | 求解失败不产生成功提交；适配器不直接写 world manifest/事件 |
| AI 提案 G2d | 接收版本化观察/目标与模型、提示、数据版本及预算；产出带来源和置信/拒绝信息的候选提案 | 权威规则验证器或人工审批者消费提案；UE 可只读展示提案状态 | AI 不获得权威 state directory 写权；未知模型/超时/不合规输出显式拒绝，不隐式推进 tick |
| UE5 发布版插件 G2c | UI/输入层可发显式 `advance`，但命令 ID 与预期 revision 必须可追踪；其他呈现操作只发 `status/observe` | 把固定 revision/tick 的样本投影到 Actor/Renderer；相机、帧率和暂停只改变视图 | 无响应、错 world/revision、水位不符时显示错误或保留旧画面并标记，不伪造新状态 |

**版本建议：**协议 envelope 保持 v1 兼容现有探针；当前领域 `schema_version` 存于存档身份和 `status` 结果，不是每条请求或响应的通用必填字段。若要求每条请求携带领域 schema，须另立协议兼容、旧客户端与迁移卡；本版不作此更改。规则/生成器/物理/AI 配置应各有显式版本。不要在旧字段下改变语义。`request_id` 标识一次请求/响应相关性，`command_id` 标识权威推进的幂等性；二者不可互代。跨领域状态共享须经后续 ADR 冻结 ID、单位、坐标系、序列化和迁移策略。

## 建议的最小探针与错误矩阵

固定一个已批准的 world 输入和独立 state directory，单 worker、单 UE 客户端。记录准确提交、构建、依赖/配置、请求/响应 JSONL、状态 manifest、event/head 摘要及观察时间窗口。探针顺序：`status` → `observe(tick 0)` → 显式 `advance(command A, expected_revision 0, target_tick 1)` → `observe(tick 1)` → 重放 command A → 历史 `observe(tick 0)` → 关闭/重启后 `status/observe`。每一步比对 world、tick、revision、水位与摘要；每个纯观察动作前后比对权威持久摘要。

错误探针另覆盖：过期 revision、同一 command ID 不同输入、未知/缺失历史、错误 world、未知协议/schema、物理适配失败（若纳入）、AI 拒绝/超时（若纳入）、worker 退出与 UE 响应超时。保存原始结果和预期错误代码映射；当前代码的领域错误名称作为实测输入，统一错误 taxonomy 待 G1 审查后冻结。不能以旧阶段 2 单刚体通过推断 AI、复杂物理或完整混沌世界通过。

## 分领域可执行探针输入（提案，尚未运行）

三套输入各用**新的** state directory；相同目录重启才用于恢复检查。以下 Python 片段只生成 JSONL 请求，给对应 worker 的标准输入。每轮新进程重启后发送新的 `status` 和历史 `observe`，不能把初次 `advance` 再作为新的推进。实际执行时保存命令行、退出码、原始响应和运行前后 manifest/event/head 哈希。

```python
import json

def req(op, n, world, **kw):
    return {"protocol_version": 1, "request_id": f"{world}-{n}",
            "operation": op, "world_id": world, **kw}

def emit(rows):
    print("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), end="")

# 单刚体：从全新 state directory 启动 engine/edgeworld_worker/worker.py，
# world_id=body-demo；需固定 Genesis 1.4.3、设备、dt、步数和 seed。
body = "body-demo"
b = [req("status", "s0", body),
     req("observe", "o0", body, logical_tick=0, view_spec={"camera": "probe-v1"}),
     req("advance", "a1", body, command_id="body-a", expected_revision=0, target_tick=1),
     req("observe", "o1", body, logical_tick=1, view_spec={"camera": "probe-v1"}),
     req("advance", "a1-retry", body, command_id="body-a", expected_revision=0, target_tick=1),
     req("observe", "historic", body, logical_tick=0, view_spec={"camera": "probe-v1"})]
# emit(b)  # 将输出送入该 worker 的 stdin；重启后发送 status + observe tick 0/1。

# 树：全新 state directory，启动 engine/edgeworld_worker/tree_worker.py，
# world_id=seed-tree-demo，seed=7。规则系数仍为实验模型。
tree = "seed-tree-demo"
def tree_view(w):
    return {"watermark": w, "region": "single-tree-world", "observer": "ue-default-camera-v1",
            "resolution": "single-tree-proxy-v1",
            "error_budget": {"semantic_state": "exact", "visual_geometry": "unmeasured-proxy"},
            "rules": {"evolution": "experimental.seed-tree.v1", "projection": "stylized-tree-ue-v1"}}
t = [req("status", "s0", tree),
     req("observe", "o0", tree, logical_tick=0, view_spec=tree_view(0)),
     req("advance", "a1", tree, command_id="tree-a", expected_revision=0, target_tick=1,
         environment={"phase": "shaoyang", "moisture": 0.8, "light": 0.7}),
     req("observe", "o1", tree, logical_tick=1, view_spec=tree_view(1)),
     req("advance", "a1-retry", tree, command_id="tree-a", expected_revision=0, target_tick=1,
         environment={"phase": "shaoyang", "moisture": 0.8, "light": 0.7}),
     req("observe", "historic", tree, logical_tick=0, view_spec=tree_view(0))]
# emit(t)  # 重启后发送 status + observe tick 0/1。

# 混沌：用 generate_initial_world("chaos-demo", 7) 写成 InitialWorld JSON，
# 启动 engine/chaos/origin_worker.py --initial-world <该文件> --state-dir <新目录>
# --world-id chaos-demo --seed 7。仅 O1 CHAOS→ONE，不能继续推到 tick 2。
chaos = "chaos-demo"
def chaos_view(w):
    return {"watermark": w, "region": "origin-sample", "observer": "ue-camera-v1",
            "resolution": "chaos-proxy-v1",
            "error_budget": {"semantic_state": "exact", "visual_geometry": "proxy"},
            "rules": {"evolution": "chaos-o1-exp-v1", "projection": "chaos-ue-projection-exp-v1"}}
c = [req("status", "s0", chaos),
     req("observe", "o0", chaos, logical_tick=0, view_spec=chaos_view(0)),
     req("advance", "a1", chaos, command_id="origin-a", expected_revision=0, target_tick=1,
         origin_action="reveal_world_spirit"),
     req("observe", "o1", chaos, logical_tick=1, view_spec=chaos_view(1)),
     req("advance", "a1-retry", chaos, command_id="origin-a", expected_revision=0, target_tick=1,
         origin_action="reveal_world_spirit"),
     req("observe", "historic", chaos, logical_tick=0, view_spec=chaos_view(0))]
# emit(c)  # 重启后发送 status + observe tick 0/1。
```

上述请求是设计 fixture。本版修订自检以临时目录直接调用树与混沌 `Worker.handle`，两组各六个请求均 `ok`，重复 command 的 result 相等；未验证进程 JSONL、重启恢复、UE 或 Genesis 单刚体。单刚体在此使用 `view_spec` 空间提示，树和混沌使用各自冻结的采样字段。执行卡须把准确启动命令、固定输入和 Genesis 设备参数落盘；若依赖不可用，结果记 `inconclusive`，不能称探针通过。

## 现有错误与未来统一映射

| 路径 | 当前可观察错误代码举例 | 未来分类提案；本版不改 wire code |
| --- | --- | --- |
| 三类 worker 共性 | `unsupported_protocol`, `unknown_operation`, `command_id_conflict`, `revision_conflict`, `worker_stopped`, `worker_error` | 协议、冲突、不可用、内部故障；`worker_error` 必须保留原始消息和现场 |
| 单刚体 `worker.py` | `world_not_found`, `invalid_view_spec`, `history_missing`, `tick_sequence_error`, `persistence_failed` | 身份、观察、历史、序列、持久化 |
| 树 `tree_worker.py` | 同上，另有 `invalid_environment`, `watermark_mismatch`, `unsupported_resolution`, `unsupported_rules`, `unsupported_projection` | 环境、精确切片、版本不兼容 |
| 混沌 `origin_worker.py` | `world_mismatch`, `invalid_origin_action`, `invalid_target_tick`, `phase_conflict`, `watermark_mismatch`, `unsupported_rules` | 身份、操作/阶段、精确切片、版本不兼容；`world_mismatch` 不能静默改名成 `world_not_found` |
| UE transport/client | 请求 ID 或 `protocol_version` 响应不符、超时、进程退出、JSON 无效等客户端错误；由 `EdgeWorldJsonlClient.cpp` 产生 | 传输/解析故障，与 worker 的 `ok:false/error.code` 分开记账 |

以上为代码可产生的**代表性映射**，不是完整枚举或已批准的统一 taxonomy。G1 冻结前由各领域 owner 从固定负例请求导出完整代码与预期表，再由 UE owner 规定客户端分类；不更改现有返回码来迎合提案。

## UE 响应身份校验责任

现有通用 `Exchange` 只校验 envelope 的 `request_id` 与 `protocol_version`，不通用检查 `result.world_id`、tick、revision。树专用观察解析器已有 world/tick/source revision/watermark 的精确核对；其他领域不能据此声称已实现。接口设计要求**各调用点**在使用 result 更新画面或输入状态前核对请求 world ID、所求 tick、source revision/水位及适用的规则/投影版本；`status` 和 `advance` 同样检查 world 与预期的新 revision。缺字段或不符时禁止应用该结果，保存原始 envelope 和客户端错误。若未来把校验上移到公共客户端，需兼容三种领域结果 schema，并以独立实现/测试卡交付；本设计没有修改 UE 代码。

## PDCA 卡与拓扑派工

| 项 | 内容 |
| --- | --- |
| ID / parent / owner | `G1-INTERFACE` / `G1` / 接口设计 owner；独立 reviewer 另派 |
| Plan | 固定 `5cac4a3` 与现有契约/代码；先完成接口清单和写入权划分，再列 schema 版本与错误/恢复路径，最后设计探针。依赖 G0 过程门；产品范围阈值待 G0-FREEZE。 |
| Do | 本设计提案；不改运行代码、旧契约和共享 backlog。后续 G2a/b/c/d 各自拥有非重叠实现路径，集成前由 G1 冻结共用字段。 |
| Check | reviewer 对照阶段 1、Seed→Tree 契约与三类 worker，逐项确认写者唯一、版本字段、错误路径、DAG 无环、探针可复现。实际运行探针属于后续集成卡；本轮未运行 UE/Genesis/AI；v0.2 仅完成树与混沌 Worker.handle 六步自检，正式进程/重启探针仍待 G3。证据为本文、准确输入提交、审查记录及后续原始 JSONL。 |
| Act | 发现冲突时修改最小接口卡并提升版本，保留旧探针证据；缺 G0 决定则标 `inconclusive` 并仅派不依赖的规划/基准任务。G1 接受须有独立审查及统筹集成裁决；文档提交本身不代表接受。 |

依赖 DAG：`G0 过程门 → G1-INTERFACE 设计 → 独立审查/接口冻结 → 本版本必需 G2 叶卡 → G3 探针与集成 → G4 独立验收`。`G0-FREEZE` 与 `GQ-BASELINE` 可并行推进，冻结阈值在受影响的 G2 实施/G4 判定前接入。各 G2 owner 不得独立重定义共享字段；接口变更须回到 G1 形成新版本。
