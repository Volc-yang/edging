# CHAOS-REALISM-01 / L1 日间外观与光照

`AChaosRealismLook::EnsureInWorld(UWorld*)` 是主任务唯一场景组装入口可调用的幂等函数。它只创建一个不执行 Tick 的本地呈现 actor：可移动方向太阳、实时天空光、Sky Atmosphere、低密度体积雾和无边界自动曝光偏移。样区中心为 `(50000,40000,0)` cm。所有强度、太阳角度与雾参数都是可调的呈现参数，不进入 Chaos Worker、O1 或观察契约。

当前主项目已有模板太阳和天空光；主任务组装写实样区时应使用隔离场景，并明确移除或禁用模板对应光源，避免叠加曝光。本 L1 不修改 `ChaosGameMode` 或模板资产。没有可授权的写实地表贴图、植被网格，也没有对应 PBR 材质输入，因此本模块只建立发布版 UE5.8.3 光照链路，不单独宣称写实美术通过。VolumetricCloud 需要有效云材质；当前未加入，以免创建不可见的空云组件。Lumen/Nanite 的配置与性能仍由集成和 Metal 阶段门裁决。

大型 L1 资产与预览的专用位置为 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/Assets/Look/`、`Renders/Look/`；本提交未写入外部大型资产。UE 自带组件不复制到 Git 或 DevSSD。

## 已执行检查

- UE 5.8.3 `Build.sh EdgeWorldHostEditor Mac Development -Project=<L1 EdgeWorldHost.uproject> -WaitMutex`：成功。首次编译因 UE 将“循环只返回第一个 actor”当错误拒绝，改为单次迭代查询后重建成功。
- UE 5.8.3 `Build.sh EdgeWorldHost Mac Development -Project=<L1 EdgeWorldHost.uproject> -WaitMutex`：成功。构建警告涉及安装版 MetalShaderConverter 缺少可选 include 目录，未阻断构建。
- 本模块未由 GameMode 调用，因此没有 L1 的 Metal 运行画面、材质资产或帧时间证据。此阶段只证明源码在安装版 UE 的 Editor/Game target 可编译；集成后 V1 必须实际采图并核对光照与权威状态隔离。
