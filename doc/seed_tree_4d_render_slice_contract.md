# Seed → Tree 4D 渲染纵切契约

版本：0.1（实验原型）

状态：本迭代接受的实现边界；不是生产生物学模型或已批准世界法则

目标引擎：UE 5.8.3 发布版

## 1. 迭代目标

从一个稳定身份的树种子开始，经显式逻辑 tick 演化为树；对指定历史时间与状态水位执行纯读观察；UE5 在小型生成场景中将观察结果呈现为可见的树形。验证时间切片、确定性重放和“呈现不推进权威状态”。

```text
显式环境输入 + Seed 状态 + 版本化实验规则
                    ↓ advance(command_id, expected_revision, target_tick)
        独立 tree worker（权威状态、因果记录、检查点）
                    ↓ observe(tick, watermark, SampleQuery)
     固定时间的只读状态样本 + 状态/事件摘要
                    ↓ UE 5.8.3 Runtime 插件
       Engine BasicShapes 树形代理 + 生成 PIE 场景
```

## 2. 接受的范围与约束

- 本轮是单世界、单 Seed、单树的纵切。树的健康、生物量、水分、生命周期阈值、阶段映射和时间相位系数均是实验参数，结果不得表述为真实植物规律。
- `seed_id` 与 `tree_id` 分属起源和结构身份；萌发前没有活动树结构，萌发后 `tree_id` 稳定并保留其 `seed_id` 来源。
- 树枝拓扑不作为本轮目标。UE 使用固定数量的 Engine BasicShapes 圆柱/球体形成**标量状态驱动的视觉代理**；顶点/材质/组件是可重建呈现数据，不进入权威状态或未来演化输入。
- `engine/edgeworld_worker/worker.py` 的 Genesis 刚体协议与状态保持不变。新增独立、不调用 Genesis 的树 Worker，使用独立 state directory，通过同版 JSONL envelope 和现有 UE 进程传输运行；为兼容现有启动器，接受其 `--state-dir --world-id --dt --physical-steps --seed` 参数，树 Worker 不使用物理步长参数。
- UE 5.8.3 插件、项目 Runtime/GameMode 和现有渲染组件优先；不修改 UE 引擎源码、不添加外部树木美术、不提交二进制 `.umap`。Host GameMode 在 PIE 运行时生成地面、灯光、相机和观察树 Actor。
- 任何 tick 推进只能来自显式 `advance` 请求。UE Actor/Game/Render Tick、视角、画质、暂停、重复 Observe 只影响呈现，不写树状态、不运行演化规则。

## 3. Worker 协议

沿用阶段 2 的 JSONL v1 envelope：`protocol_version`, `request_id`, `operation`, `world_id`；响应使用 `ok/result` 或 `ok:false/error`。

### `advance`

除现有字段 `expected_revision`, `target_tick`, `command_id` 外，树推进必须携带显式环境：

```json
{
  "environment": {"phase": "shaoyang", "moisture": 0.8, "light": 0.7}
}
```

单次只允许 `target_tick == current_tick + 1` 且 revision 匹配。缺失/非法环境、revision 冲突或 tick 跳跃须明确失败；同 command ID 和相同请求返回相同结果，不重复推进；同 ID 配不同输入报冲突。Seed、事件、树状态均由 Worker 权威提交。

初始状态为 tick/revision 0 的未萌发 Seed。各阶段只能按版本化规则向前转换；萌发后形成独立 `tree_id`。每次成功推进记录 Seed/Tree 身份、tick、revision、command ID、规则版本、环境输入摘要、原因码、前态/后态摘要和前序事件摘要。

### `observe`

观察请求的 `view_spec` 必须绑定固定采样条件：

```json
{
  "watermark": 3,
  "region": "single-tree-world",
  "observer": "ue-default-camera-v1",
  "resolution": "single-tree-proxy-v1",
  "error_budget": {"semantic_state": "exact", "visual_geometry": "unmeasured-proxy"},
  "rules": {"evolution": "<ruleset-version>", "projection": "stylized-tree-ue-v1"}
}
```

`watermark` 必须精确匹配请求 tick 对应的已提交 revision。历史不存在或水位不匹配时返回明确错误，不得回退到当前状态。响应带请求 tick、source revision、水位、seed/tree ID、生命周期阶段、表现所需标量、相位、规则/投影版本、state hash 和 event hash。重复同一查询须返回相同样本。

响应字段固定如下，UE parser 不得各自发明别名：

```json
{
  "world_id": "seed-tree-demo",
  "logical_tick": 3,
  "source_revision": 3,
  "watermark": 3,
  "sample": {
    "seed_id": "seed-7",
    "tree_id": "tree-<stable-derived-id-or-null-before-germination>",
    "stage": "seedling",
    "health": 0.8,
    "biomass": 0.3,
    "water_reserve": 0.4,
    "phase": "shaoyang",
    "ruleset_version": "<version>"
  },
  "projection_version": "stylized-tree-ue-v1",
  "state_hash": "<digest>",
  "event_hash": "<digest>",
  "view_spec": {"watermark": 3, "region": "single-tree-world"}
}
```

阶段枚举固定为 `seed | seedling | mature | declining | dead`；萌发前 `tree_id` 为 JSON `null`，tick 0 的 `phase` 也为 `null`。Observe 顶层 `logical_tick` 必须等于请求 tick；`source_revision` 与请求及回显的 `watermark` 必须指向同一历史快照。`sample.ruleset_version` 和 `projection_version` 必须与请求的版本清单匹配。Python/UE 序列化的整数遵守 JSON 精确整数上限 `2^53-1`。

## 4. UE5 视觉代理

- Host GameMode 运行时生成一个 BasicShapes 地面、灯光、固定观察相机和树观察 Actor，以避免外部美术与二进制地图依赖。
- 观察 Actor 无 Tick，仅由已验证的 Observe 样本更新。stage/biomass 按 `stylized-tree-ue-v1` 映射到树干高度/粗细与固定树冠组件尺度；种子/幼苗/成树具有可辨别的外观。相位可以作为纯呈现提示，但不可反向进入规则或状态哈希。
- 同一已提交样本必须映射为相同组件数量、变换和材质参数。LOD/真实植物几何、资产美术和物理碰撞不在本迭代范围。

## 5. 阶段门

1. Python：固定 Seed 与显式环境序列可逐 tick 重放得到相同状态/事件摘要；覆盖萌发到成树、边界输入、幂等、revision 冲突、历史精确观察、重复观察只读和 worker 重启恢复。
2. UE：UE 5.8.3 Host/插件 Editor target 构建通过；从树 Worker 响应更新观察 Actor，不由 UE 帧推进状态。
3. 时间切片：至少观察萌发前、幼苗、成树三个精确 tick/watermark；相同查询重复后样本摘要和树形代理参数相同，历史缺失明确失败。
4. 可见渲染：PIE 使用真实 RHI 显示代码生成的场景和树，并留存固定相机的萌发前/成长后画面或等价视觉证据。NullRHI 只证明协议/状态隔离，不证明画面可见。
5. 只读呈现：改变相机/帧率、暂停恢复渲染、重复 Observe、显隐观察 Actor 前后，worker tick/revision/state/event hash 和持久 manifest 摘要不变；只有显式 Advance 改变它们。

本迭代不承诺 cook/package、跨 OS/GPU 一致、量化后的植物几何误差、真实生态规律、多树资源竞争、Genesis 植物物理或生产性能。若真实 RHI 可见证据受环境限制，应记录为未验证，不把编译/NullRHI 结果升级为渲染门通过。
