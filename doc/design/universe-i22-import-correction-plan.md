# I22 PDCA：先验证Native能力，再保存真实资产

2026-11-10；parent=I21/D3-IMPORT；root统筹。上下文基线`545117db10e20434f43a841863b1b09b2b0b3323`；实现前置为未合并的`codex/i21-import@cd3b26fde5655b77482daa051eb2eb00c2c55359`/草稿PR130，复用其干净`.worktrees/i21-import`。计划**待独立C0接受**，本轮没有UE派发或实现改动；不用goal。

## P：修复范围与判定

I21确切失败是StaticMeshEditorSubsystem返回None而在保存前调用其方法；源码提示所属动态模块未启动，但这还不是已实测的唯一根因。新增独立能力probe，以发布版公开`unreal.load_module('StaticMeshEditor')`激活模块后重新取实例，在导入任何外部资产前实际调用所需getter/临时对象操作。probe通过后才导入原I20组合，完成真实保存、Native正/负例及新进程reload。不能仅用callable/头文件、内存创建或CI代替Native通过。

固定UE5.8.3 CL58210709；I20源root和index `d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7`不变。目标仍5 StaticMesh/14 Texture2D/3 UMaterial；fern独立alpha/Masked0.5/TwoSided、PBR/ARM线性通道、GL原件与显式DX覆盖、ground预览球禁作地形保持。ground只交付纹理/材质。本轮不接Universe/worker/Genesis、不改现有Host/GameMode/parser/I0A/权威/引擎源码，不授Metal画质/物理/历史只读门。

首轮显式`pipeline.mesh_pipeline.build_nanite=false`，回读真实Nanite设置；分别记录source glTF、native render LOD0、native Nanite input计数，后两者由实际Native getter取得。保持严格source triangles与局部AABB阈值，不改源fixture或放宽容差。该策略是最小几何导入验收，不预判最终产品Nanite/画质策略。

## 任务树 / 排他卡

```text
P0固定失败/方案 → C0独立接受
 → A能力probe + 模块激活/显式Nanite策略 + 原导入/回读窄修（复用PR130）
 → C1准确source/argv/环境/预算与启动来源审查
 → R: probe（无磁盘资产写入）→ import → reload → seal
 → C2独立原件/真实包与材质/输入不变/资源/退出审查
 → root父级复核、PR状态/上下文commit；只有真正通过才考虑接受源实现
```

| 节点 / owner / 写范围 | Plan / Do | Check / evidence | Act |
| --- | --- | --- | --- |
| P0 / root + A只读planner | 固定两种基线、probe结果与导入的依赖、预算/停止条件 | C0审方案与真实安装源码 | 接受后派A实现，不再一轮泛研究 |
| A / i20_assets_plan；原i21-import树/branch，base cd3b26f；仅`scripts/realism_import/`、`tests/test_realism_import.py`、`doc/evidence/universe-I22A/` | 公开模块激活、真正能力probe、显式非Nanite策略/字段、I22独占准备路径与probe/import/reload；不改I21报告/失败/原快照。source提交固定后才交root运行 | 必要CPU/AST及真实文件preflight；C1审具体API；实际能力和包验收由R。更新原草稿PR130，不另开实现PR | 缺能力先失败，不导入半套；真实错误只返工该叶，不改旧失败或返回常量伪证 |
| C / i20_review；审定后`.worktrees/i22-review`/`codex/i22-review`从计划commit；仅`doc/evidence/universe-I22C/` | C0只读；C1审source/确切卡；C2重读日志/包/Node连接/负例及资源原件 | 固定所有字节/SHA/真实父wait，分开probe、实际导入、CPU及视觉；非自报判定 | 独立accept/rework/partial，报告按root审读/摘取等效证据门集成，不自行UE/merge |
| R / root；`doc/evidence/universe-I22R/`、登记/backlog/本计划；DevSSD新root | 唯一真实UE执行/资源监督。复用I21已审工具思路，I22单独artifact/card，不改任何I21原路径 | 实际Popen/wait、全输入终检、项目Content完整map/包sidecar/SHA、两Native结果、后代静默/外域/后验封存 | 全部必要门通过才接受；失败留原件，按本卡停止条件结算，不隐藏重试 |

## 能力probe的真实内容

1. 清环境/检查startup与安装依赖后，显式load StaticMeshEditor；固定AdvancedPreviewScene等实际依赖文件SHA。返回新取的真实subsystem class/实例身份；若仍None立即fail，不在此冒称根因已修。
2. 固定SHA的安装Cube/DefaultTexture仅作为技术fixture；实际读取LOD/vertices/UV/sections/slot/collision/bounds/render/Nanite getter，不用hasattr作成功证据。
3. 经公开SystemLibrary.duplicate_object克隆到TransientPackage，在临时副本上实际运行section/slot修改与恢复、纹理flags、临时材质连接/断开/恢复；输出真实回读。原Engine包不修改/不保存，不把bounds center冒充pivot。临时对象不得进项目Content。
4. probe之前后项目Content为空、安装fixture和所有源输入SHA不变；probe不生成/保存真实资产，不授导入/材质来源/画质门。导入模式仍独立执行模块/能力前置检查，不能用另一个进程的实例充当前置状态。
5. import/reload必须实际记录source node→UE mesh，class、units/axis/local origin/bounds、section/slot/材质、texture source/normal/sRGB/ARM/Alpha连接，完整项目与安装依赖闭包、全部uasset/sidecar文件SHA。实际内存断Alpha/错slot要得到准确拒绝、恢复且不保存负例。reload是全新进程，读取已封存包，完整正例快照相等且Content map前后不变；失败不回退BasicShapes。

## 新资源卡与停止条件

- 新root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import`，不复用/改写I21；每个probe/import attempt各有独占host、UserDir/log/result/DDC/tmp，重试同样独占。reload打开选定成功import的同一Host/Content（或完整复制并逐字节核对后的新副本），仅UserDir/log/result/DDC/tmp独占，禁止空host/重新导入。尽可能在首派发前完成全部源码审查、安装SHA、静态卡与准备；reload只晚绑定实际成功包/结果SHA。
- 自首probe派发至最终fsync后封存连续≤1200s，新root总逻辑文件≤4GiB；**项目host/Content**合计≤512MiB，DDC/Content另列缓存但仍计总量。最多2次probe（各≤90s）、2次import（各≤240s）、1次reload（≤180s）；每次返工只动受影响叶。probe未过禁止import；import未过禁止reload。到达次数/时间/字节上限或余量不足即结算partial，不重置clock；probe/import各不超过2次、reload仅1次。
- Cmd/NullRHI/unattended/NoTrace/FileSystem Isolated DDC/NoDefaultGraph和确切`UE_SKIP_UBT_SDK_SETUP=1`沿已审安装源码保留；不调用C++build、不授SDK门。清UE_PYTHONPATH/PYTHONHOME/PYTHONPATH/EDGEWORLD，受控环境白名单；真实Foundation Documents、启用plugin闭包/pip要求及所有Content/Python启动源检查继续执行。
- root追踪真实Cmd/app及已知后代，超时仅回收精确本次进程；forced不算正常。遍历遇错拒绝，项目Content只regular且禁link；已知tmp内诊断IPC仅实际lstat类型/bytes记录、不读取。六个声明外域保持原检查；意外写入/残留不pass。原I21监督器和UBT失败不因此消除。
- 每个Native阶段严格按C1的实际argv/env/输入SHA；没有必要时不重跑已通过CPU/CI。失败后先诊断原件，窄修和新准确卡仍计原clock；若改变执行入口/依赖或契约，先版本化修订与独立审查，不临场偷偷换框架。

验收：能力先检、5/14/3真实保存与Native负例、独立reload、输入/文件/资源/正常退出、独立C2和父级复核分别pass，才允许把D3-IMPORT标为接受。PR130的CI/草稿状态不自动替代这些门；用户此前明确只批准草稿公开发布，任何merge另按审查门和授权处理。
