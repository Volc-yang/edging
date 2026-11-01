# I5 恢复与纯观察统筹接受（2026-11-01）

PR [#82](https://github.com/Volc-yang/edging/pull/82)，source `49f7b7a849068ea5d49b07f1f77f5f45719e0577`，merge `09ed3bb360a659a5eb5442706bd4e153cf545d75`。仅recovery.py/专属测试；主统筹读取完整API/实现，首check前纠正Mapping插入顺序隐含依赖，I5按raw key/hash/world/refs在纯内存构造确定topological顺序并覆盖全部pinned对象，不依赖Store私有实现。recover完整校验后才调用D_recovery；sync失败只接受fresh unconfirmed_readonly，坏/缺历史引用拒读，无fallback/求解/初始化。status/observe仅Snapshot、exact tuple/watermark和返回副本。

Owner首次batch16tests通过（0.319秒、runner0.395秒、exit0）；3.10grammar、准确干净source、输入前后SHA不变。包括反序合法Mapping等价输入、孤立/缺失/坏hash、历史损坏、W9/sync只读、同tick多revision与纯读文件map不变。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I5-20261101-recovery-attempt1/raw-index.json`，SHA `0b6ee4d6954a79459080812488c425c0b2ecf9f79f1fcf5194e4d0bce8baffb3`；root独立复算10/10索引size/hash及14现场rows内488/488 raw_hex摘要一致。

最终head CI verify success（run41323313667/job124897933412）。root review接受后expected_head合并；source已为merge祖先且worktree干净后清理 `.worktrees/i5-universe-recovery`，保留branch/证据。未使用targeted rerun、未运行UE/Genesis；I5 complete，G-S1独立进程故障门仍planned，等I4接受后派fresh非I1–I5作者。
