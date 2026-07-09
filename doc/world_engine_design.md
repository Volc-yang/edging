### **《易之世界》世界引擎设计草案**

#### **1. 核心设计思想**

我们的引擎将遵循开发手册中定义的核心法则：

*   **空间 (宇) = 八卦**: 世界的空间地理特征由八卦的基本属性决定。
*   **组合 (卦象)**: 整个世界地图将被划分为64个区域，每个区域对应《易经》六十四卦中的一卦。每个区域的地形将由其对应的卦象（由两个八卦重叠而成）共同决定。

#### **2. 八卦与地形特征映射**

我们首先为八个基础卦象定义其对应的地形“基元”属性。这将作为程序化生成算法的“参数”输入。

| 卦象 | 卦名 | 象征 | 核心地形特征 | 游戏内表现 |
| :--- | :--- | :--- | :--- | :--- |
| ☰ | **乾 (Qián)** | 天 | **崇高, 广阔** | 雄伟的高原、接近天空的最高山峰。 |
| ☷ | **坤 (Kūn)** | 地 | **平坦, 承载** | 广袤的平原、盆地，地形平缓，适合文明生长。 |
| ☳ | **震 (Zhèn)** | 雷 | **动态, 震动** | 断裂的地形、峡谷、地震后的破碎地貌。 |
| ☴ | **巽 (Xùn)** | 风 | **流动, 渗透** | 连绵起伏的丘陵、风蚀地貌、大面积的草原或沙漠。 |
| ☵ | **坎 (Kǎn)** | 水 | **险陷, 深邃** | 深邃的河谷、大型湖泊、沼泽、危险的深渊。 |
| ☲ | **离 (Lí)** | 火 | **光明, 附着** | 火山地貌、炎热的沙漠或戈壁、地热活动区域。 |
| ☶ | **艮 (Gèn)** | 山 | **静止, 阻隔** | 连绵的山脉、天然的巨大屏障、难以逾越的区域。 |
| ☱ | **兑 (Duì)** | 泽 | **喜悦, 汇聚** | 湿地、三角洲、小型湖泊群、充满生机的浅水区域。 |

#### **3. 六十四卦与区域生成**

世界地图将被看作一个 **8x8 的宏观网格**，每个格子代表六十四卦中的一卦。

*   **卦象决定区域**: 每个格子的地形由其对应的卦象决定。一个卦象由“上卦”和“下卦”组成。
    *   **下卦 (内卦)**: 决定该区域的**基础地貌**。例如，下卦为“艮”(山)，则该区域基调是山地。
    *   **上卦 (外卦)**: 为基础地貌**附加额外的特征或变化**。例如，一个区域是“山”(`艮`)，如果上卦是“火”(`离`)，就组成了**火山旅**卦，代表这片区域是“火山山脉”。如果上卦是“水”(`坎`)，就组成了**山水蒙**卦，代表这片区域是“被水环绕的群山”或“多瀑布的险峻山岭”。

*   **生成算法**:
    `地形最终高度 = 基础高度(下卦) + 特征变化(上卦) + 柏林噪声()`
    *   每个卦象都会被翻译成一组柏林噪声的参数（如基础高度、噪声频率、振幅、层数等）。
    *   卦象组合的规则将决定这些参数如何叠加和调整。

#### **4. 数据结构提议**

为了在代码中实现上述设计，我们可以定义以下结构体：

```swift
// 在一个新的文件中，例如 WorldEngine.swift

// 1. 定义八卦枚举
enum Bagua: Int {
    case Qian = 0, Kun, Zhen, Xun, Kan, Li, Gen, Dui
    // ... 可以添加更多与卦象相关的属性
}

// 2. 定义地形生成参数
struct TerrainParameters {
    var baseHeight: Float       // 基础海拔
    var roughness: Float        // 崎岖度 (振幅)
    var featureScale: Float     // 地貌尺度 (频率)
    // ... 可以添加更多参数，如湿度、温度等
}

// 3. 定义卦象组合（六十四卦之一）
struct Hexagram {
    let innerBagua: Bagua // 内卦（下卦），决定基础地貌
    let outerBagua: Bagua // 外卦（上卦），决定附加特征
}

// 4. 定义世界引擎核心
class WorldEngine {
    // 存储从卦象到地形参数的映射规则
    private var rules: [Bagua: TerrainParameters] = [:]

    init() {
        // 在这里，我们将步骤2表格中的设计，转化为代码规则
        setupRules()
    }

    private func setupRules() {
        // 例如：
        rules[.Gen] = TerrainParameters(baseHeight: 0.6, roughness: 0.8, featureScale: 0.5) // 艮为山
        rules[.Kun] = TerrainParameters(baseHeight: 0.1, roughness: 0.1, featureScale: 0.2) // 坤为地
        // ... 定义所有8个基础卦象的规则
    }

    // 核心函数：根据一个卦象，计算出最终的地形参数
    func getParameters(for hexagram: Hexagram) -> TerrainParameters {
        guard let innerParams = rules[hexagram.innerBagua],
              let outerParams = rules[hexagram.outerBagua] else {
            // 返回一个默认值或处理错误
            return TerrainParameters(baseHeight: 0, roughness: 0, featureScale: 0)
        }

        // 此处是设计的核心：如何组合内外卦的参数
        // 简单的例子：基础海拔由内卦决定，崎岖度由内外卦共同影响
        let finalRoughness = (innerParams.roughness + outerParams.roughness) / 2
        
        return TerrainParameters(baseHeight: innerParams.baseHeight, 
                                 roughness: finalRoughness, 
                                 featureScale: innerParams.featureScale)
    }
}
