# I18：直接复测已合入 NoTrace Native 封存修复

2026-11-07；用户“继续”授权 I17 唯一入口，输入a19ea4f。产品/native5a6cca0，工具已含PR123/124最终CI和独立审查通过的无$筛选、短FileSystem DDC、NoTrace flags、sponsor归属、writer barrier。不新增产品代码，不重新编译，不重复CI；旧失败保留，不授Metal/G-B2。

DAG：0方案/固定driver只读独立审查 → P离线source/binary/新原件冻结与ready → T同一已获权限driver一次Native并自动after采证/资源seal → A独立原件与formal exact3 review → 上下文commit/push/依赖清理。root唯一运行owner；reviewer不UE/build/worker/UI、不读owner/key。driver是本轮可审计执行原件，不是新引擎/工具框架；先语法核对与独立审查，再冻结source。

输出沿原I15 output_root完整计量，I18-20261107-native-seal新子目录+run绑定短DDC，旧owner/context/input/product/native/binaries保持，新prepared/card/manifest/provenance显式版本。外部六候选域（Zen/UBT两个/DDC两个/Trace）取metadata before/after，不读取其内容。所有权限/准备/ready在firstdispatch前完成，不把I17卡/计时重置成新通过。

T仅一UE窗口，Native180s/每卡global900s/2GiB；controller固定五条JSONL：诚实skip Metal→freeze manifest→start Native→actualwait→seal。完整driver自动在其后重核三frozen原件、actual ps/61-file map/外域变化、保存whole-resource review和外层wait；不在活跃clock等待分段人工或权限。watchdog/异常按已接受exact-owned cleanup，不伪装normal，不自动再跑。

Check：Found4/四完整Success/case3原始SHA和strict output、真实argv/env/PID/start/parentwait0、连续observer、实际DDC路径/NoTrace且无sponsored残留、console在writer barrier/controller seal及driver after全匹配、authority不变、声明写域与完整budget。独立review沿用现有native_replay.py，不放宽旧条件；不完整仍fail/inconclusive。A/doc/push离线工作不伪造成运行观测。下一步只由真实结果决定。
