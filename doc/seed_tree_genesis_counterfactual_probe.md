# G2 Genesis 两相反事实短探针

状态：2026-11-01，输入提交 `4cbb6b2`；仅验证 [工程 fixture](fixtures/abstract_seed_genesis_v1.md) 预声明的两相数值差异。用户允许结束旧 UE 会话后，统筹任务已结束其 UE/Worker 并确认退出；本任务没有启动 UE、修改用户状态目录或运行组合 worker。

## Plan / Do

在 macOS 26.6.2、Python 3.12.14、`genesis-world 1.4.3` Metal 后端，用仓库 `worker.py` 的公开 `GenesisAdapter` 独立进程构建两份相同初始 scene：单 Sphere，初始位置 `(0,0,1)`、半径 `0.1`，`dt=0.01`、`physical_steps=8`、`seed=7`。分别调用 `advance("shaoyang")` 和 `advance("taiyang")`，每次先采初态，再采后态。使用 `Decimal.from_float`、精度 2000、`ROUND_HALF_EVEN` 计算 `influence_mm`。每相再从全新进程/scene 重复一次；进程有 180 秒超时，实际四次退出码均为 0。

原始脚本、各进程 stdout/stderr 和机器可解析摘要位于 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/stg-genesis-probe-637Lbp/`。`probe_once.py` SHA256 为 `1070cb6de0f0de12542cb08fadec8d4b75c964eb2149ef25c4624d394dee0509`，`run.py` 为 `5a5ed6d208cc764574497c667b5b88485fe27e9e3039cf691afb3d458fcb97b3`；初次 `summary.json` 为 `5f8d00719c3baba61dee28419d95e73fb99deee1d483661d280f0d08093e9b8a`，重复 `repeat/summary.json` 为 `71ec2ca1374c4c8b0e0ec68dc182343878d3e83c80d5734a2f1802f2ad33f7f8`。两个 summary 的路径字段不同，但四次物理结果按相位逐项相等。原始文件仅本机 DevSSD 可直接复核，跨机器需按哈希转存。

## Check：实际输出

| 相位 | 初始 `z` | 推进后 `z` | 推进后 `vz` | `influence_mm` | 重复运行 |
| --- | ---: | ---: | ---: | ---: | --- |
| `shaoyang` | 1.0 | 0.9927999973297119 | -0.15999998152256012 | -7 | 结果逐字段相同 |
| `taiyang` | 1.0 | 0.964684009552002 | -0.7847999930381775 | -35 | 结果逐字段相同 |

预声明的 `influence_mm(taiyang) < influence_mm(shaoyang)` 为 `-35 < -7`，**短探针通过**；两个结果均处于 fixture 的 ±1000 mm 范围。每相两次的 `before`/`after` 向量及 `influence_mm` 完全相同。两相原始 stdout SHA256 分别为 `b039cbccba76e06928d34c7db28c2ee70f256e8a733147d49715650d4364071a`、`8bb3ea08aabd4ade97803e3fee043d321748201b2b48679a6e7559bc8bf100ee`，重复进程亦相同。stderr 含依赖警告，SHA256 为 `20e997e855cf5a7596cbc33e4ce42413d2108d9a7bcd7b6045ad1fff98bf7af1`；无运行错误。

## Act 与限制

此结果只证明现有 Genesis 适配器在固定单刚体配置下，两种受支持相位产生可区分且重复的物理候选，并且 fixture 的整数派生值可计算。它**没有**验证组合权威 manifest/事件/恢复、物理结果对抽象发展节点的实际写入、UE 呈现、性能或产品物理规律。统筹可据此独立审查 schema/fixture 的数值可行性；G2-AUTHORITY 和 G2-UE 仍须按 S4 的共享接口冻结与任务门另行发布。
