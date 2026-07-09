# edging 世界引擎建模

## 1. 建模目标

`edging` 世界引擎的目标，是把《易之世界》的哲学设定转化为可实现、可验证、可扩展的模拟系统。它不是单纯的地图生成器，而是一个由“卦象结构、时间节律、能量守恒、熵扰动、实体生命周期、玩家降神行为”共同驱动的世界模型。

本建模文档承接：

- `edgeWorld_develop_handbook.md`：世界观、三才循环、定数/变数/熵、降神玩法。
- `world_engine_design.md`：八卦地形、六十四卦区域、程序化地图生成。
- `engine/mathEdge.py`：八卦/六十四卦编码、变卦、综卦、错卦、京房八宫。
- `edge-world Shared/Renderer.swift`：当前 Swift/Metal 地形渲染原型。

## 2. 核心抽象

### 2.1 世界层级

世界被分为四层：

1. **Era 纪元层**：周、连仙、灭世，决定全局规则集、美术基调、资源密度、文明强度。
2. **Hexagram Region 卦域层**：世界宏观划分为 64 个卦域，每个卦域对应一个六十四卦。
3. **Tile 地块层**：每个卦域内部由网格地块组成，承载高度、湿度、温度、阴阳气、五行倾向、熵值。
4. **Entity 实体层**：玩家、NPC、生物、植物、遗迹、势力节点等，统一受生命周期和能量交换规则约束。

### 2.2 易学结构

引擎内部采用统一的 6-bit 卦编码：

- 低 3 bit：下卦，表示基础地貌与内在属性。
- 高 3 bit：上卦，表示外部影响与动态变化。
- bit 方向：沿用 `mathEdge.py` 的 bottom-to-top 表示，避免 Python 原型和 Swift 实现分裂。

每个卦象至少提供这些派生信息：

- `innerTrigram`：基础地貌。
- `outerTrigram`：附加地貌/气候/事件倾向。
- `lines[6]`：六爻状态，用于局部变动与事件触发。
- `changedHexagram`：由玩家行为或世界事件触发的变卦。
- `overturnedHexagram`：综卦，用于镜像区域、反向视角或时代回响。
- `interchangedHexagram`：错卦，用于对立生态、隐藏势力或反命运事件。
- `palace`：京房八宫归属，用于区域族群、势力谱系、长期演化关系。

## 3. 静态世界模型

### 3.1 数据结构草案

```swift
enum Era: Int, CaseIterable {
    case zhou
    case lianxian
    case mieshi
}

enum Trigram: UInt8, CaseIterable {
    case kun = 0b000
    case gen = 0b001
    case kan = 0b010
    case xun = 0b011
    case zhen = 0b100
    case li = 0b101
    case dui = 0b110
    case qian = 0b111
}

struct HexagramId: Hashable {
    let rawValue: UInt8

    var lower: Trigram { Trigram(rawValue: rawValue & 0b000111)! }
    var upper: Trigram { Trigram(rawValue: rawValue >> 3)! }
}

struct RegionId: Hashable {
    let x: Int
    let y: Int
}

struct WorldSeed: Hashable {
    let value: UInt64
}
```

### 3.2 卦域模型

```swift
struct HexagramRegion {
    let id: RegionId
    let hexagram: HexagramId
    var terrainRule: TerrainRule
    var climateRule: ClimateRule
    var eventBias: EventBias
    var entropy: Float
    var stability: Float
}
```

卦域不直接存储全部地块数据，而是存储生成规则和动态状态。地块可以按需生成、缓存或分块持久化。

### 3.3 地块模型

```swift
struct WorldTile {
    let regionId: RegionId
    let localX: Int
    let localY: Int
    let hexagram: HexagramId
    var height: Float
    var moisture: Float
    var temperature: Float
    var yinQi: Float
    var yangQi: Float
    var entropy: Float
    var biome: BiomeKind
}
```

约束：

- `yinQi + yangQi <= tileEnergyLimit`
- `entropy` 不直接等于随机值，而是由行为、事件、气候和实体死亡/诞生积累。
- `biome` 是结果，不是输入；它由卦象、地形、气候、阴阳气和纪元共同推导。

## 4. 动态世界模型

### 4.1 时间系统：宙 = 四象

时间不是简单帧计数，而是四象循环：

```swift
enum TimePhase: Int, CaseIterable {
    case shaoyang
    case taiyang
    case shaoyin
    case taiyin
}

struct WorldClock {
    var era: Era
    var cycle: UInt64
    var phase: TimePhase
    var phaseProgress: Float
}
```

四象对世界的影响：

- `shaoyang`：生发，实体出生率、植物恢复、探索事件上升。
- `taiyang`：鼎盛，资源产出、文明活动、战斗冲突上升。
- `shaoyin`：收敛，衰败、疾病、势力变动、因果回收增强。
- `taiyin`：寂灭，低活跃、高危险、隐藏事件和轮回判断增强。

### 4.2 能量系统：道生一

世界总能量不是每帧精确物理守恒，而是作为模拟预算：

```swift
struct EnergyBudget {
    let worldTotal: Float
    var terrainEnergy: Float
    var entityEnergy: Float
    var civilizationEnergy: Float
    var latentEnergy: Float
}
```

规则：

- 地形、实体、文明、潜能之间可以转移能量。
- 高能量区域更容易诞生实体、资源和事件。
- 高熵会降低能量利用效率，推动收敛事件。

### 4.3 熵系统：变数来源

熵是世界偏离稳定态的程度，分三层：

```swift
struct EntropyState {
    var local: Float      // Tile/Entity 级扰动
    var regional: Float   // Hexagram Region 级扰动
    var global: Float     // Era 级扰动
}
```

熵来源：

- 玩家降神干预。
- 战斗、死亡、资源掠夺。
- 大规模建造或破坏。
- NPC 势力冲突。
- 卦象变动、爻变、纪元临界事件。

熵结果：

- 低熵：世界稳定，事件可预测，资源恢复平缓。
- 中熵：奇遇、副本、势力变化出现。
- 高熵：灾害、战争、天命反噬、区域变卦。
- 临界熵：触发收敛事件或纪元更迭。

## 5. 实体建模

### 5.1 ECS 最小组件

```swift
struct EntityId: Hashable { let rawValue: UInt64 }

struct PositionComponent {
    var regionId: RegionId
    var tileX: Int
    var tileY: Int
}

struct QiComponent {
    var yinQi: Float
    var yangQi: Float
    var capacity: Float
}

struct LifecycleComponent {
    var phase: LifecyclePhase
    var age: Float
    var vitality: Float
}

enum LifecyclePhase: Int {
    case birth
    case flourishing
    case decline
    case death
}

struct FateComponent {
    var mainLine: HexagramId
    var behaviorVector64: [Float]
    var entropyTrace: Float
}
```

### 5.2 实体演化规则

实体每个模拟 tick 执行：

1. 从地块吸收或释放阴阳气。
2. 根据阴阳比例和环境状态更新生命周期。
3. 根据自身行为产生局部熵。
4. 与附近实体交换影响。
5. 在死亡时将能量回流到地块或区域。

## 6. 玩家与降神模型

### 6.1 玩家不是实体，角色才是实体

系统中区分：

- `Player`：外部操作者，拥有账号、偏好、降神记录。
- `Avatar`：世界内角色，是实体系统的一部分。
- `GodDescentSession`：玩家短时接管角色的干预窗口。

```swift
struct GodDescentSession {
    let playerId: String
    let avatarId: EntityId
    let startWorldTime: WorldClock
    var intentVector: [Float]
    var entropyInjected: Float
    var changedLines: [Int]
}
```

### 6.2 定数与变数

定数：

- 由 `behaviorVector64` 聚合得到。
- 映射到一个主卦 `mainLine`。
- 决定下一阶段主线命运、出生条件、核心挑战。

变数：

- 由 `entropyTrace` 与区域熵共同决定。
- 映射到事件池、副本、奇遇、隐藏 NPC、势力转折。
- 不覆盖主线，而是在主线旁制造偏航。

## 7. 世界生成流程

### 7.1 初始生成

1. 输入 `WorldSeed` 和 `Era`。
2. 生成 8x8 卦域网格。
3. 每个卦域绑定一个 `HexagramId`。
4. 下卦生成基础地貌参数。
5. 上卦叠加气候、危险度、资源倾向。
6. 四象时间状态修正温度、湿度、生长率。
7. 生成地块高度、湿度、阴阳气、初始熵。
8. 按能量预算投放初始实体。

### 7.2 地形参数映射

```swift
struct TerrainRule {
    var baseHeight: Float
    var roughness: Float
    var moistureBias: Float
    var temperatureBias: Float
    var resourceBias: Float
    var dangerBias: Float
}
```

建议初始映射：

| 卦 | 地貌倾向 | 参数重点 |
| --- | --- | --- |
| 乾 | 高原、天空、稀薄资源 | 高海拔、低湿度、高视野 |
| 坤 | 平原、盆地、文明承载 | 低崎岖、高资源、低危险 |
| 震 | 裂谷、雷暴、断层 | 高崎岖、高熵、高事件 |
| 巽 | 丘陵、风蚀、草原 | 中海拔、高流动性 |
| 坎 | 河谷、湖泊、深渊 | 高湿度、低洼、高危险 |
| 离 | 火山、沙漠、地热 | 高温、低湿度、高能量 |
| 艮 | 山脉、屏障、洞窟 | 高海拔、高阻隔 |
| 兑 | 湿地、泽国、汇聚 | 高湿度、高生命密度 |

## 8. 与当前代码的落地关系

### 8.1 当前 Swift 原型

`Renderer.swift` 当前已经具备：

- `Bagua` 枚举。
- `Cell` 网格数据。
- `World` 网格生成。
- Perlin noise 高度生成。
- Metal mesh 构建和渲染。

但它还缺少：

- 稳定 seed。
- 六十四卦区域结构。
- `HexagramId` 数据层。
- 时间/熵/阴阳气模型。
- 地形规则表。
- 网格更新后 mesh 重建策略。

### 8.2 推荐实现顺序

1. 新增 `WorldEngine.swift`：定义 `Trigram`、`HexagramId`、`TerrainRule`、`WorldTile`。
2. 把 `Renderer.swift` 中的 `Bagua` 替换为 `Trigram`。
3. 把随机八卦噪声改为 8x8 卦域映射。
4. 加入固定 `WorldSeed`，保证同 seed 可复现。
5. 将 `Cell` 扩展为包含 `hexagram`、`yinQi`、`yangQi`、`entropy` 的 `WorldTile`。
6. 将颜色逻辑从 `Renderer` 移到规则层，渲染只消费结果。
7. 引入 `WorldClock`，先只影响湿度/光照，再扩展到实体模拟。
8. 最后接入实体系统和降神会话。

## 9. Python 原型与 Swift 实现的边界

短期建议：

- Python `mathEdge.py` 继续作为算法验证和数据生成工具。
- Swift 侧实现运行时最小子集：八卦、六十四卦、变卦/错卦/综卦。
- 通过 JSON 导出规则表，避免 Swift 直接依赖 Python。

可生成的数据文件：

- `models/trigrams.json`
- `models/hexagrams.json`
- `models/terrain_rules.json`
- `models/palace_rules.json`

## 10. 最小可验证原型

第一个可验证目标不是完整开放世界，而是：

1. 启动 App 后生成一个固定 seed 的 8x8 卦域世界。
2. 每个卦域有不同地貌和颜色倾向。
3. 鼠标/键盘暂时可不做，先自动旋转观察。
4. 每 10 秒推进一个四象阶段。
5. 阶段切换时，湿度、亮度、颜色或熵可见变化。
6. 打印当前卦域、四象、全局熵，方便调试。

验收标准：

- 同一个 seed 每次生成结果一致。
- 64 个卦域能在地图上被辨认出来。
- 调整某个 `TerrainRule` 后，对应卦域地形变化明显。
- 时间阶段变化不会破坏 mesh 或造成明显卡顿。

## 11. 风险与取舍

### 11.1 复杂度风险

原设定包含开放世界、动态生态、离线 AI、服务器模拟、轮回与命运系统。若同时推进，会导致系统边界失控。应先锁定客户端可视化世界引擎原型。

### 11.2 算法风险

易学规则不能只做符号贴图，否则会变成装饰。至少要让卦象影响：地形、气候、事件倾向、实体生命周期中的两个以上维度。

### 11.3 性能风险

当前 `Renderer.swift` 只在首次构建 mesh。后续如果地形动态变化，需要分块 mesh、脏块更新或 GPU 侧高度图，否则每帧重建 150x150 mesh 会浪费 CPU。

## 12. 下一步工程任务

- 新建 `edge-world Shared/WorldEngine.swift`，承载纯模型和生成逻辑。
- 清理 `Renderer.swift` 中压缩成一行的 mesh 生成代码，提高可维护性。
- 增加 `WorldSeed`，去掉不可复现的 `UInt32.random`。
- 把 `models/` 变成规则数据目录，先提交 `terrain_rules.json`。
- 用 `mathEdge.py` 导出六十四卦基础表，作为 Swift 侧数据对照。
