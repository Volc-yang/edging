# import02 实际失败与下卡输入

本轮两次 import 额度已消耗；不启动第三次，不以 reload 重导。root 记录 import02 约26.4s、parent wait255、非强制、后代静默，source pins 不变。`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import/a2/result.json` 实际 FAIL 为 `NoneType.enable_section_collision`；`a2/ue.log:1197–1208` 确认 `do_import()` 的 StaticMeshEditorSubsystem 为 None。流程只在内存执行了真实导入与材质创建，尚未完成最终 save_loaded_assets、Native 正例/负例/新进程回读，未交付保存包。C2 实际枚举确认 a1/host/Content、a2/host/Content 均为空、没有 `.uasset`；R 的保守 content_bytes=2,679,781 来自 a2/ddc/Content 中两份 `.udd`，该计数包含 DDC 缓存，不能代替原生资产包或导入通过证据。

## 安装源码诊断

- `Engine/Source/Editor/EditorSubsystem/Public/EditorSubsystem.h:8–15`：EditorSubsystem 为动态系统，在所属模块 StartupModule 后实例化；StaticMeshEditorSubsystem 没有 commandlet 禁用 override。`SubsystemCollection.cpp:641–726` 由 ModuleLoaded 更新动态实例。a2 日志没有 StaticMeshEditor 模块启动记录；最强解释为 owning module 未正常启动/注册，不把该推断说成已运行验证的唯一原因。
- `PythonScriptPlugin/.../PyCore.cpp:1271–1303,2071`：公开 `unreal.load_module('StaticMeshEditor')` 使用 FModuleManager 并导入 Python bindings，是下一卡可验证的发布版适配。`StaticMeshEditorModule.cpp:26–30` 的 StartupModule 会加载 AdvancedPreviewScene，因此下一卡要固定这项实际模块依赖并继续 NullRHI/无窗口约束，不能把 module activation 冒称已经通过。
- `EditorStaticMeshLibrary.cpp:141–145,216–222` 的 deprecated API 只是转发同一 subsystem，None 时返回空/无操作，不能替换为伪成功。
- `EditorScriptingHelpers.cpp:143–160` 的 section API guard 检查主线程、GIsEditor、非PIE；未直接禁止 commandlet。不能由此推断未启动模块后的全部getter必定可用，仍须真实执行。

## Nanite 与计数语义

安装 `InterchangeGenericMeshPipeline.h:130–141` 默认 `bBuildNanite=true`、threshold0；a2 日志1087–1141实际运行了NaniteBuild。`StaticMesh.cpp:5004–5012` 的 GetNumTriangles(0) 读取 render LODResources；可能是 Nanite fallback，不等于源 glTF triangles。`GetNumNaniteTriangles()` 读取 Nanite resources 的 NumInputTriangles，也要与源/渲染字段分列，不套同一名字。

下一卡建议明确将受控 pipeline `build_nanite=false`，再实际读取该设置和 render count；保留源期望/实际render LOD0/实际Nanite input三种语义，严格源局部AABB与三角数匹配不放宽。若保留Nanite，应另冻结 source→Nanite input→fallback 的验证关系，不能调大容差或以fallback数字重写源fixture。

## 本次最窄补丁与未验证项

只增加 `required_static_mesh_subsystem()` 前置检查，main 在任何导入/创建/保存前拒绝缺失 subsystem，其余调用复用同一清晰错误。没有自动 load_module、deprecated fallback、recipe/Nanite策略修改或重跑。AST检查通过；该 guard 尚未经过 UE 执行。先前 preflight 文件身份属于各自原提交，不能拿旧 snapshot SHA 授权这份新脚本。

下一PDCA先审定并实现：显式已安装模块激活 → 首个能力检查（subsystem及required getters） → 新独占Host真实导入 → Native快照/故障恢复 → 单独新进程回读。原a1/a2、失败计量和全部源输入保留；真实导入门仍未通过。
