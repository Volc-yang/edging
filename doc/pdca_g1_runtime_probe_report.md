# G1 分领域进程 JSONL 短探针

状态：2026-11-01，v0.1；输入提交 `4d3f8d2`，对应 [G1 v0.2 设计](pdca_g1_interface_design.md)。只检查树与混沌两个独立 Python worker；未运行 Genesis、UE 或产品场景。

## Plan / Do

使用 Python 3 从本 worktree 启动 `python3 -m engine.edgeworld_worker.tree_worker --seed 7` 与 `python3 -m engine.chaos.origin_worker --initial-world models/chaos/initial_world_seed7.json --seed 7`；各加独立 `--world-id` 和 `--state-dir`，均位于 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/g1-probe-6m6uj22e/`。每类顺序发送 `status(0)`、`observe(0)`、`advance(1)`、`observe(1)`、重复同一 `command_id`、历史 `observe(0)`，关闭进程后从原状态目录重启，再发送 `status`、`observe(0)`、`observe(1)`。全部请求和完整响应、每次请求前后状态目录文件 SHA256、启动参数、退出码与 stderr 保存在原始 JSON；请求字段按 G1 v0.2 领域 fixture。没有接触用户运行中的 UE/Worker 或其状态目录。

## Check：实际结果

| 检查 | 树 | 混沌 |
| --- | --- | --- |
| 首进程六步与重启三步响应 | 9/9 `ok:true`，两进程退出码 0 | 9/9 `ok:true`，两进程退出码 0 |
| `advance` 与重复命令 | result 完全相等；重复前后状态文件 SHA256 相同 | result 完全相等；重复前后状态文件 SHA256 相同 |
| 历史与重启观察 | tick 0/1 的 result 与重启后对应 result 相等 | tick 0/1 的 result 与重启后对应 result 相等 |
| 后续纯观察、重启 `status` | `observe` 各步和重启 `status` 前后状态文件 SHA256 相同 | 同左 |
| 初次 `status` 前后文件 | 空目录变为 `tree_world.json`；与进程启动初始化重叠，不能将变化归因于 `status` | 空目录变为 `world.json`；同样不能将变化归因于 `status` |

因此，**已初始化世界的历史观察、重启状态读取和重复命令不改持久文件**这一有限门通过。初次启动与首个 `status` 的时间窗无法分离，若需证明从进程启动瞬间起的纯读语义，应另作启动握手和文件稳定点检查；不将本次首个 `status` 判为只读失败或通过。探针脚本的汇总 `pass:false` 是因为它把初始文件出现也计入了只读比较；原始记录保留此保守结果，本报告按分项证据裁决。

原始证据（本机 DevSSD，未纳入 Git）：

| 领域 | 原始请求/响应及文件哈希 | 进程记录 |
| --- | --- | --- |
| 树 | `tree/raw.json` SHA256 `c79a7d90b6312efbafe3bae84a830f9dc756c0c10e4108cf293d82c4f690e23b` | `tree/process.json` SHA256 `06a1a3f1ad1fab3efcd4669bd94895e47aeabb9fae3bb1a8c1f9d6e9df7eed4f` |
| 混沌 | `chaos/raw.json` SHA256 `f094cf2c8e5d5ea026a3b561b41a7d4fff298fe139cbd728b652b34614eea8a1` | `chaos/process.json` SHA256 `af8a6d00628d94214427a186ef82a655896e674ad5310aa4f148d44e086704d0` |

路径均相对上述探针根目录。`summary.json` SHA256 为 `1b31eff63a24c4adb6d1c900254cfe3f89976a9ffa3b840f95e24460e5183124`。原始目录留存供统筹独立复算；尚未验证跨机器可达性。

## Act

G1 可将树/混沌进程协议探针列为**有限通过**，但共享接口冻结仍需统筹核对结果身份、负例错误矩阵以及本版本选定的必需领域。Genesis、UE、初次状态初始化的精确边界和产品端到端验收继续开放。若复核发现原始哈希或响应不符，只重开本探针，不修改已完成的独立设计审查。
