# PDCA-CHAOS-01 / C1 独立状态核查

日期：2026-10-27。结论：**C1 有限 Python 阶段门通过**。本结论仅覆盖 seed 7、`chaos-demo`、本机单进程单写者的初态、O1、历史只读观察和恢复；不覆盖 UE 真实 RHI、跨平台逐位一致性、多写者或长期归档。

## 审查范围

- 固定基线：`5dc6b6a9115cc504062f937741d47cae2fd42d35`；P0 契约：`doc/chaos_origin_contract.md`。
- D1：PR #2，集成提交 `3e7a8c2`，新增初态校验、地理生成、固定输入及测试。D2：PR #3，集成提交 `f7eaef8`，新增权威运行时、单 manifest 存储、JSONL Worker 及测试。已检查两份集成提交的文件清单与实现 diff；D2 对详细地理校验调用 D1，O1 由 Worker 负责持久化。
- 输入：`models/chaos/initial_world_seed7.json`；启动：`python3 -m engine.chaos.origin_worker --initial-world models/chaos/initial_world_seed7.json --state-dir <独立临时目录> --world-id chaos-demo --seed 7`。临时目录由 `tempfile.TemporaryDirectory(prefix='chaos-c1-')` 创建，未触碰 PIE/树 Worker 状态。

## 独立协议探针

用 Python `subprocess.run` 向上述 CLI 逐行发送 JSONL：`status → advance(command_id=origin-o1, expected_revision=0, target_tick=1, origin_action=reveal_world_spirit) → observe(0, watermark=0) → observe(1, watermark=1) → 重复 advance → observe(0, watermark=1)`。退出码 0，前五项 `ok=true`；最后一项 `watermark_mismatch`。观察请求使用 P0 的 `origin-sample` 区域、`ue-camera-v1` 观察者、`chaos-proxy-v1` 分辨率和实验规则版本。

| 对象 | 实测 SHA-256 / ID |
|---|---|
| InitialWorld canonical hash | `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3` |
| tick 0 state hash | `e2030df396ae7f1f5c1466e475ac467d09daf397be52d3b983386402d88f3d0f` |
| tick 1 state hash | `d6b6ec5b7543fe9dfa486708f4013425b4a63c9c734ec8da3720552c552cbb8c` |
| tick 1 event hash | `3b7a8899f219bde5207c2e754391b54c9212e56b04dece2b4acbb8aa4450548f` |
| world spirit ID | `spirit-597eac36f6d6c494` |
| committed `world.json` raw SHA-256 | `5b9311df6cf84dfa36fba8f961566367a91a02c49ae1da7a58c2ffac4d381057` |

tick 0/1 历史 Observe 分别返回上述状态哈希。重复同一 command ID 的结果对象与首次相等。关闭进程后用同一状态目录新启 CLI，`status` 返回相同 tick 1 state/event hash；再次 Observe 的结果相同，`world.json` 原始 SHA 未变。另建空目录以同一 seed/版本重建：tick 0 manifest 原始 SHA 为 `a889d9400fcbada2e6aafb977665f12a0d227fc700bac6ac4123fdd45dabb36d`，再次 O1 后 manifest 原始 SHA 与首轮一致。

## 边界及故障

- 非法 target tick 返回 `invalid_target_tick`；修改河道终点使其不抵达海洋，初始化返回 `invalid_initial_world`。
- 在已提交 manifest 的事件中篡改 `cause_code` 后重启，返回 `corrupt_state`。
- 用 `unittest.mock.patch` 使临时文件创建报磁盘满：Advance 返回 `persistence_failed`，manifest 原始 SHA 不变。使目录 fsync 在 replace 后报错：返回 `commit_status_uncertain`，同进程随后的 status 返回 `worker_stopped`；重启从磁盘恢复 tick 1。这是故障注入，不是物理磁盘故障实测。
- 执行 `python3 -m unittest tests.test_chaos_origin_runtime tests.test_chaos_world_generation -q`：14 项通过。

上述独立探针先因报告脚本误取 Observe 结果中不存在的 `event_watermark` 字段中断；修正报告字段读取后完整重跑，得到本报告结果。该中断未修改源码或权威状态。

## 阶段门裁决与开放项

固定初态摘要、O1 一次提交、重复命令幂等、错误水位拒绝、历史只读、重启恢复、损坏数据拒绝与提交失败 fail-stop 均有本机可重复证据，C1 通过。UE 真实画面与相机/帧率/暂停/显隐对权威摘要的隔离属于 C2；跨 OS/GPU、并发 writer lock 和长期归档仍开放。未发现需交 D1/D2 修复的 C1 阻断缺陷。
