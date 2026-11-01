# G1-INTERFACE 独立代码审查

状态：2026-11-01，v0.1；审查输入为 `617eb5c`，被审提案为 `doc/pdca_g1_interface_design.md`。本报告审查设计与当前代码的相符程度，不执行新运行探针，也不批准产品语义。

## Check 范围与结果

只读核对 `engine/edgeworld_worker/worker.py`、`tree_worker.py`、`engine/chaos/origin_worker.py` 和 UE `EdgeWorldJsonlClient.cpp`。当前三类 worker 均以 JSONL v1 的 `protocol_version`、`request_id`、`operation`、`world_id` 路由 `status/observe/advance`；推进使用 `command_id`、`expected_revision`、`target_tick`，UE 客户端也有对应方法。设计中的这些字段是**现有有限协议字段**，并非全部是新增项（`worker.py:280-310,336-354`；`tree_worker.py:349-378,447-467`；`origin_worker.py:103-129,137-157`；`EdgeWorldJsonlClient.cpp:311-338,463-468`）。

| 发现 | 代码依据 | 对 G1 冻结的影响 |
| --- | --- | --- |
| 三个 worker 共用 envelope，但状态和观察 schema 不同 | 刚体 `worker.py:317-334` 返回 body transform/hash；树 `tree_worker.py:388-445` 要求 `view_spec` 中的 watermark/region/observer/resolution/error_budget/rules；混沌 `origin_worker.py:118-128` 走 origin `observe_result` | 设计正确提示不能把三个 worker 当作可互换运行时。冻结前需选定本版探针所测领域与精确 fixture。 |
| 最小探针作为通用模板尚不能原样运行 | 树观察必须提供完整 `view_spec` 和精确 watermark（`tree_worker.py:388-402`）；混沌 O1 推进还需 `origin_action="reveal_world_spirit"` 且只接受 tick 1（`origin_worker.py:137-157`）；刚体推进由内部 phase 决定（`worker.py:336-357`） | G1 应给各领域一个具体请求序列，不能只写 `observe(tick)` / `advance(A)` 作为可执行规范。建议先用既有单刚体 fixture 跑通 envelope，再给树与混沌独立探针。 |
| `schema_version` 目前主要是领域 `status` 返回和存档身份，不是每条请求通用必填字段 | `worker.py:301-306`、`tree_worker.py:369-374`、`origin_worker.py:118-123`；UE `SendOperation` 仅设置 envelope 字段（`EdgeWorldJsonlClient.cpp:463-468`） | 设计中的独立 schema 版本方向合理，但若要求请求/每条结果携带它，属于**未来协议变更**，须另立兼容与迁移卡。 |
| 错误代码不统一，UE transport 另有客户端错误 | `worker.py:287-315`、`tree_worker.py:356-382`、`origin_worker.py:109-134`；UE 处理请求 ID、协议版本及超时/退出（`EdgeWorldJsonlClient.cpp:138-253`） | 设计已标 taxonomy 待冻结；G1 需先列现有逐领域错误映射，区分 worker 业务错误与 UE transport 错误。 |
| UE transport 验证响应请求 ID 与 v1，但通用 Exchange 不验证结果中的 world/tick/revision | `EdgeWorldJsonlClient.cpp:221-253`；树专用解析器才核对精确 world/tick/revision/watermark（同文件 `510-542`） | 设计中“错 world/revision、水位不符时标记”只能声称树观察路径已有部分实现；其他领域须在具体调用点检查或补契约。 |
| `request_id` 与 `command_id` 的角色分离与代码一致 | `worker.py:280-310,339-347`、`tree_worker.py:349-378,449-462`、`origin_worker.py:103-129,137-150` | 可作为 G1 不变量；重复 command 用相同 payload 取得存档结果，换 payload 报 conflict。 |

## Plan / Do / Check / Act 裁决

- **Plan：**固定单领域 fixture、准确提交、独立 state directory 和预期错误码，再逐领域设计 status→observe→advance→observe→重复命令→历史 observe→重启恢复；保持 AI/Genesis 产品范围待 G0 裁决。
- **Do：**本文仅审查；未修改协议、worker、UE 或旧契约。
- **Check：**代码位置与提案逐条对照完成；设计边界方向可接受，但通用探针和“所有 UE 路径已做结果身份校验”的推断不得作为已通过门。运行证据仍为 `planned`。
- **Act：**建议 G1 提案进入下一版修订：补三套领域 fixture、现有错误表、观察结果身份校验责任点，并将 `schema_version` 请求扩展明确标为未来变更。完成修订和独立审查后方可冻结共享接口；G2 领域实现继续等待 G0 范围与对应接口裁决。
