# I21-A importer / Native producer handoff

2026-11-10；base `6eae2795628dc10d94506b00f37084fe4ae4e488`，branch `codex/i21-import`。状态：实现与 CPU owner 检查已交付，C1/实际 UE 运行/新进程回读 pending。没有启动 UE、GPU、worker、Genesis 或写 DevSSD，也没有读取 owner/key。

## 交付

`scripts/realism_import/` 包含独立 content-only descriptor、清 startup/extra path/pip/remote 的项目配置、固定真实 I20 源 recipe、stdlib 预检/排他准备、root dispatch argv/env 和 UE 内实际 importer/metadata producer。唯一新增测试 `tests/test_realism_import.py` 不导入 unreal、不 mock Native API。范围外产品文件和 I20 原件均不修改。

实现目标：5 StaticMesh / 14 Texture2D / 3 UMaterial。受控 Interchange stack 关闭 combine、bake meshes、bake pivot、collision、自动材质/纹理；图像独立导入后显式 PBR。GL 原件保留并使用独立 Texture2D；真正材质 Normal 选择额外 DX source，禁重复翻绿。地表仅纹理/材质，不导入其球。

Native producer 从真实 UObject getter 读取 class、LOD0 triangle/vertex、bounds、section→slot/material、texture importData 的实际源文件及 SHA、纹理尺寸/采样参数、UMaterial 实际 property input 和输出通道。源 mesh/node 映射由实际三角数和局部 AABB 对比固定源范围决定，不按对象名伪造。源单位/轴约定另列，不冒充实际 getter。mesh-local 原点语义与测得 bounds center 分开；没有虚构独立 DCC pivot 数值或完整 runtime profile。

先保存正例，再真实断开 fern OpacityMask、将 fern mesh slot0 改绑岩石材质，实际读回应拒绝，再恢复并核对正例快照相同，全程不保存负例。reload 必须新 commandlet 读取已保存包，重新调用所有 getters，与 import Native snapshot 比较；Content 全文件 SHA 前后保持不变。包依赖遍历包括项目包与安装版外部 content 的实际包/sidecar SHA，未知 /Game 外部依赖拒绝。

## 已执行检查

- `python3 -B -m unittest tests.test_realism_import -v`：4 项通过；真实20文件及复制 Alpha 缺失/损坏、路径/链接/证据不可覆盖、严格 JSON、环境/未知用户 startup 拒绝。`cpu-check-final.txt` 为实际输出。
- `python3 -B scripts/realism_import/prepare.py preflight`：ready_requires_C1_and_root_dispatch；实际 UE5.8.3 CL58210709，20 源文件，698 个安装 Content/Python 文件、23 个相关安装 dylib 身份已记录于 `preflight-final.json`。SHA `4f5e75c4fe4335a21931a41b61f776946a887fec9e51bd748cde7c56f50e3e00`。
- AST 解析全部 producer/preparation Python 成功；没有执行 `ue_entry.py`。最终 preflight 的 snapshot_sources 与当前源字节一致。
- 第一组 CPU 临时目录使用 macOS `/var` 别名，触发显式拒绝 symlink；保留 `cpu-check-attempt1.txt`。将测试新目录根换为系统临时目录的 canonical 路径后重跑通过，没有放宽产品路径检查。实现草稿的一处未闭合括号也在 AST 检查中发现并修正，未运行到 UE。

这些检查只证明 CPU 输入边界和已安装文件身份；所有反射 API 的实际执行尚待 root。Native getter 若不匹配，UE 结果明确 FAIL 并保留日志，不以常量或宽泛 fallback 补结果。

## Root 执行入口

先复查精确 PR/source，再运行 README 中的 stdlib preflight/prepare。`prepare.py import --attempt 1` 只建立新 `I21-20261110-import/a1` 并输出具体 dispatch；由 C1 对该 argv/env/job SHA 审核后 root 以 argv list、shell=False 监管执行。`-script` 只有无空格 script path，job 在相邻会话根，由独立环境 pin `I21_IMPORT_JOB_SHA256` 绑定，避免 Mac script 参数引号解析问题。清所有继承 EDGEWORLD/PYTHON/UE_PYTHONPATH/loader 注入，仅 root dispatch 新增受控 job pin 与 TMPDIR。

成功后 root 调 `prepare.py reload --attempt 1`，再审准确新 job/argv，以新进程、独占 user/log/DDC 复载。若 first import 失败，仅按冻结卡的相同连续 clock 授权一次窄修和 a2，新 Host/Content/Saved/DDC 不覆盖 a1。代码不自行启动、重试、回收任何进程。

root 监管职责：最多 2×240s import + 1×180s reload，首 dispatch→seal 总900s，全部 root≤4GiB / 所有 Content≤512MiB，实际 parent wait 和后代静默、外域 before/after map、源前后身份及最终包封存。producer PASS 不能代替这些门，更不能授 Metal/视觉/法线外观、world/Genesis、HUD 原子性。

工作树在独立 PR 审核/实际测试/集成之前保留；资产源及全部失败原件不清理。
