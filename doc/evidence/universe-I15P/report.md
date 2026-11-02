# I15 P：existing 只读能力探针（交付待统筹审查）

父节点 I15；基线 `ee138aea8178f7d09082caf7448f6e1090719b11`。本卡交付源码和 CPU 检查；**没有执行 UE、Native tests、Genesis、实机输入、截图、准备或 freeze**。因此没有真实能力通过或 G-B2 授权。

## Plan / Do

新显式 `EDGEWORLD_UNIVERSE_DIAGNOSTIC_SCOPE=readonly-probe` 只接受 actual session=existing、initialize=false 且已验证 Pins.AllowedActions 为空。p1 aliases 保留真实 session，使用实际 handler/callback/getter 原点、event_serial 和日志 offset。p1.probe 使用实际 FViewport 像素、GDynamicRHI 名称和相同 viewport HDR 标记。旧 s1/s2 gate、standard manifests 和 parser 没有放宽。

Native 源码提交 `997eda058d545b87889681871cc01c2cf68f1637` 已冻结。新增 `ReadonlyProbeScope` 是额外 source-only test；本轮固定四 selector 不包含它，不能声称它被实际执行。

`probe_actions.py` 提供独立 manifest/receipt/evidence/schema。固定 11 action、48 个 CUA 调用、8 张原图、4 business request（status/observe/observe/observe）、interaction proposal 210s≤300s。其成本是提案，尚无实际时长。每 action/子阶段要求新 map、raw tool ref、step_id、原日志 brackets 和 checkpoint order；任何写请求/重试、重用 map、错来源或恢复失败均拒绝。所有成功仅为一致性，真实来源、PNG、wait、资源由 root/controller 和独立审查负责。

`prepare_probe.py` 默认只读 audit。显式执行才独占创建固定新 root，派生 existing/false/[] owner、复制四份逐字节相同公共输入、用纯 typed parser 导出 public pins、建立五个输出链接及批准 DefaultInput.ini。它不 provision、不迁移或改动 authority、不读取/枚举/hash 私钥，仅 lstat key directory 本身。源/Genesis package/native/Python lexical chain/HEAD 必须匹配历史 accepted 输入。`freeze_prepared` 必须在 root 真实构建成功之后，核对 actual Native git bytes、RPATH 和二进制后独占生成 prepared。缺文件或失败不补造、不覆盖、不自动重试。

## Check / Act

实际运行 `python3 -B -m unittest tests.test_universe_iteration_probe tests.test_universe_iteration_actions tests.test_universe_iteration_actions_v2 -v`：43/43 pass（12 新定向 synthetic、31 旧合同回归），约 2.1s。覆盖实际格式/serial/step/raw-call/map/Metal-SDR-dimensions/FPS 分支、额外写/缺 action、只读默认准备、有限元数据派生和独占写入。合成原件明确 synthetic，不用于运行验收。Native 编译和工具 readiness 留 root。

状态：源码交付完成、运行能力未验证。推荐独立审查 → 独立 PR CI → 合入 → root 按下面两阶段执行。保留所有失败与新输出，不能把仅 helper 写入的 receipt 当成真实 build/wait 证据。

## Root 交接命令

工具来自合入后的干净集成 worktree，产品为包含 N/P 真实 C++ 的独占 build/live worktree。两者不同，避免输出链接污染 tool source 身份。默认命令先不加 `--execute` 审计；实际准备再加该 flag，返回 preparation_ref（path/SHA）。

```sh
python3 -B TOOL/doc/evidence/universe-I15P/prepare_probe.py --product-root PRODUCT --tool-root TOOL --run-id i15-20261102
python3 -B TOOL/doc/evidence/universe-I15P/prepare_probe.py --product-root PRODUCT --tool-root TOOL --run-id i15-20261102 --execute
```

Root 持有 CPU 构建资源卡后，在 PRODUCT 执行官方 `scripts/launch_edgeworld_ue_mac.sh --build-only --universe`。保留原始父进程 wait 和失败，再封存 build receipt；至少 `source_sha`=准确 native source commit、`actual_parent_wait_exit=0`、`build_only=true`、`ue_runtime_started=false`；N 需要的 source_refs/binary_refs 可放同一 receipt。之后：

```sh
python3 -B TOOL/doc/evidence/universe-I15P/prepare_probe.py --tool-root TOOL --freeze --execute --preparation-sha256 PREP_SHA --build-ref /absolute/public/build-receipt.json --build-sha256 BUILD_RECEIPT_SHA --native-source-sha NATIVE_COMMIT
```

结果固定 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe/prep/prepared.json`。精确36字段见 helper `FIELDS`，C 必须实际复核各源/权限/路径/引用，不信 `audit_only` 或 passed 标签；root 发有效期能力卡后才能启动。原 owner 仅 refs，不含原文；runtime pin 只包含公开安装文件。默认 audit 会读 owner 元数据用于核对，绝不读 key bytes。
