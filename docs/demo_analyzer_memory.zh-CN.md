[English](demo_analyzer_memory.md) | [Français](demo_analyzer_memory.fr.md) | [简体中文](demo_analyzer_memory.zh-CN.md)

<a id="cs2guard--demo-analyzer-project-memory"></a>
# CS2Guard — 演示分析器项目内存

<a id="1-purpose"></a>
## 1. 目的

本文件记录了**CS2Guard 演示分析器**项目的开发过程。

其目的并非取代主程序 `README.md`，而是提供项目更详细的技術記錄：

* 实现了哪些功能；
* 每个功能引入的原因；
* 每个功能的工作原理；
* 代码库中涉及的哪些部分；
* 实现过程的测试方法；
* 开发过程中做出的技术决策。

演示分析器对应于 CS2Guard 的 **v0.x** 开发阶段。

其长期目标是分析《反恐精英 2》演示文件，并提取有意义的游戏行为特征，以便后续用于识别可疑玩家行为。

---

<a id="m1--demo-parsing-foundation"></a>
# M1 — 演示解析基础

<a id="objective"></a>
## 目标

M1 的目标是为 CS2Guard 建立数据提取的基础。

在尝试检测可疑行为之前，项目首先需要将原始的《反恐精英 2》`.dem` 文件转换为可被后续分析阶段处理的结构化 Python 数据。

简化形式如下：

```text
CS2 Demo (.dem)
      ↓
 Demo Parser
      ↓
Structured match data
      ↓
Players / Rounds / Ticks / Events
```

<a id="main-features"></a>
## 主要功能

<a id="demo-parsing"></a>
### 演示解析

CS2Guard 可加载并解析《反恐精英 2》演示文件。

解析器提供了比赛级别的信息以及比赛期间记录的游戏行为数据。

<a id="match-metadata"></a>
### 比赛元数据

可以从演示文件中提取基本元数据，例如描述比赛和演示本身的资讯。

这为分析的数据提供了上下文信息。

<a id="players-and-teams"></a>
### 玩家与队伍

提取并标准化玩家信息，以确保在整个分析过程中能够一致地识别玩家。

这包括以下信息：

* 玩家姓名；
* Steam ID；
* 队伍信息。

<a id="round-data"></a>
### 回合数据

比赛可以被划分为回合，以便后续在正确的游戏情境下分析事件和玩家行为。

<a id="tick-level-player-data"></a>
### 逐帧玩家数据

可以提取玩家状态随时间的变化。

这为诸如移动和瞄准分析等时间维度特征提供了基础。

重要信息包括：

* 玩家位置；
* 视角角度；
* 当前使用的武器；
* 在演示文件中特定时刻的玩家状态。

<a id="gameplay-events"></a>
### 游戏事件

提取了若干重要的游戏事件。

<a id="shots"></a>
#### 射击

表示一名玩家执行的武器射击行为。

有用信息包括射击玩家、武器和射击时间。

<a id="hits"></a>
#### 命中

表示对另一名玩家造成的伤害。

命中事件提供以下信息：

* 攻击者；
* 受害者；
* 武器；
* 伤害值；
* 命中部位；
* 时间点。

<a id="kills"></a>
#### 击杀

表示玩家被消灭的情况。

击杀事件包含以下上下文信息：

* 攻击者和受害者；
* 武器；
* 头颅命中状态；
* 距离；
* 穿透情况；
* 烟雾交互；
* 无瞄准镜状态。

<a id="data-normalization"></a>
## 数据归一化

原始解析输出会被转换为内部CS2Guard结构。

目标是防止项目其余部分直接依赖于演示解析库返回的表示形式。

概念上：

```text
Raw demo data
      ↓
DemoParser
      ↓
Normalization
      ↓
CS2Guard models
```

这种分离将使后续分析组件更易于维护和测试。

<a id="testing"></a>
## 测试

解析基础由自动化测试覆盖。

一个重要的设计决策是避免让主测试套件依赖于一个本地`test.dem`文件，该文件在仓库或CI环境中未必可用。

真实演示文件仍可手动用于集成和可视化测试。

<a id="result"></a>
## 结果

在M1阶段结束时，CS2Guard已具备将CS2演示数据转换为适合特征提取的结构化信息的功能基础。

因此，项目可以从：

> "CS2Guard能否读取一场比赛？"

转变为：

> "CS2Guard可以从这场比赛中提取出哪些有用的行动特征？"

---

<a id="m2--aim-feature-extraction"></a>
# M2 — 瞄准特征提取

<a id="objective-1"></a>
## 目标

M2的目标是将M1阶段提取的原始视角信息转化为可重用的**瞄准移动特征**。

俯仰和偏航值描述了玩家的视线方向，但单独来看不足以用于行为分析。因此，M2引入了一层特征提取机制，描述玩家瞄准随时间的变化过程。

概念上：

```text
Tick-level view angles
        ↓
Angle normalization / deltas
        ↓
Angular velocity
        ↓
Angular acceleration
        ↓
Rolling temporal features
        ↓
Aim behavior analysis
```

这些特征构成了演示分析器的第一个行为特征家族。

<a id="main-features-1"></a>
## 主要特征

<a id="angle-processing"></a>
### 角度处理

瞄准计算基于从连续演示帧中提取的玩家俯仰和偏航值。

偏航需要特殊处理，因为角度在`-180° / +180°`边界处会循环。因此，像`179° → -179°`这样的过渡必须被解释为一个微小的旋转，而不是几乎360°的旋转。

归一化的角度差确保了速度和加速度计算能够真实反映瞄准移动情况。

<a id="angular-velocity"></a>
### 角速度

角速度衡量玩家视角方向在样本之间的变化速率。

俯仰和偏航分别独立计算速度，使水平和垂直瞄准移动能够保持可区分。

概念上：

```text
angular velocity = angular displacement / elapsed time
```

这可以描述缓慢跟踪、正常瞄准修正、快速旋转以及类似‘快速扫视’的移动行为。

仅高角速度并不被视为作弊的证据。

<a id="angular-acceleration"></a>
### 角加速度

角加速度衡量角速度随时间的变化速率。

概念上：

```text
angular acceleration = change in angular velocity / elapsed time
```

它有助于表征瞄准动作中的突变变化，包括快速鼠标移动的开始或结束。

较大的加速度值可能由于快速抖动、方向快速变化、离散演示采样和短时间间隔而自然出现。因此，加速度是一种行为特征，必须结合额外上下文进行解释，而不是作为一个独立的作弊指标。

<a id="rolling--temporal-aim-features"></a>
### 滚动/时间序列瞄准特征

单个时间步长之间的测量值可能具有噪声，仅能提供玩家行为的局部描述。

当前实现是在选定的时间窗口上计算统计量，而不是滑动的滚动统计序列。这些时间特征总结了短时间内的瞄准序列，并为后续分析提供了更稳定的信息。

时间计算基于演示时间步长数据设计；其解释必须保持对CS2时间步长/子时间步长记录行为的意识。

<a id="shot-centered-aim-sequences"></a>
## 以射击为中心的瞄准序列

在手动验证时，M2可以检查选定射击周围的瞄准序列。

可视化流程暴露了以下上下文信息：

* 玩家；
* 目标；
* 武器；
* 射击时间步长；
* 在适用情况下，命中时间步长。

然后可以检查射击周围的窗口，以理解玩家在开火前后瞄准行为的变化。

<a id="aim-visualization"></a>
## 瞄准可视化

使用专用的可视化脚本进行M2特征的手动检查。

职责划分如下：

```text
scripts/parse_demo.py
    → M1 parsing / structured demo inspection

scripts/visualize_aim.py
    → M2 aim feature inspection / visualization
```

生成的图表允许直观查看选定射击周围瞄准相关值的演变。它们是开发和验证工具，而非最终的作弊检测机制。

<a id="weapon-context"></a>
## 武器上下文

选定的射击序列还暴露了玩家所使用的武器。

武器名称来自演示数据。例如，`elite`对应双贝雷塔。

武器上下文可能在将来变得有用，因为合法的瞄准行为可能因武器和射击情境而异。在M2中，它仍属于上下文信息，而非可疑性标准。

<a id="implementation-structure"></a>
## 实现结构

瞄准特征提取与演示数据摄入是分离的。

概念上：

```text
src/cs2guard_demo/parser/
        ↓
normalized tick/event data
        ↓
src/cs2guard_demo/features/aim.py
        ↓
aim features
        ↓
scripts/visualize_aim.py
```

这使得特征提取可以被后续的检测或机器学习组件重用，而无需依赖可视化代码。

<a id="testing-1"></a>
## 测试

M2通过自动化测试覆盖了瞄准特征提取逻辑。

这些测试独立于本地`.dem`文件验证特征计算，确保了主测试套件的可重现性和适用于持续集成（CI）。

仍可通过`visualize_aim.py`手动使用真实演示文件进行集成和可视化验证。

在M2结束时，所有自动化测试均通过。

<a id="technical-decisions"></a>
## 技术决策

M2期间做出的重要决策包括：

* 从归一化的时间步长数据中导出瞄准特征，而非直接从原始解析输出中获取；
* 在移动计算前处理角度的环绕。
* 保持俯仰运动的可区分性；
* 将速度和加速度视为描述性信号而非直接的作弊指示器；
* 使用滚动统计来提供时间上下文；
* 采用以射击为中心的序列，便于人工实际检查；
* 保持自动化测试与已提交的演示文件相互独立；
* 保持`parse_demo.py`专注于M1，`visualize_aim.py`专注于M2。

<a id="result-1"></a>
## 结果

M2已完整并经过验证。

CS2Guard现在能够将原始视角数据转化为结构化的瞄准行为特征，并在射击和击中等游戏事件周围检查这些特征。

演示分析器已从：

> "玩家在看哪里？"

发展到：

> "玩家的瞄准行为随时间如何变化，尤其是在战斗动作期间？"

这些瞄准特征提供了首个可被后续与其他特征家族和检测逻辑结合以识别可疑游戏行为的行为信号。

---

<a id="m3--dataset-builder"></a>
# M3 — 数据集构建器

<a id="objective-2"></a>
## 目标

M3的目标是将前几个里程碑产生的结构化比赛数据和行为特征转化为适用于机器学习工作流的可复现数据集。

CS2Guard不再需要手动分析单个演示文件，现在可以处理多个比赛的集合，并生成标准化样本，这些样本可后续用于训练、验证和评估。

概念上：

```text
Multiple match sources
        ↓
Source ingestion / adapters
        ↓
Canonical CS2Guard representation
        ↓
Feature extraction
        ↓
Dataset samples
        ↓
Train / validation / test splits
```

<a id="main-features-2"></a>
## 主要功能

<a id="multi-demo-processing"></a>
### 多演示文件处理

数据集构建器可以自动处理多个演示文件，而无需对每场比赛单独进行分析。

这使得可以从多个CS2比赛集合中构建更大的数据集，同时保持处理流程的可复现性。

<a id="event-level-samples"></a>
### 事件级样本

游戏事件可以转换为独立的数据集样本。

这些样本保留了事件上下文，同时以适用于后续机器学习阶段的格式暴露了特征。

<a id="player-level-samples"></a>
### 玩家级样本

CS2Guard还可以在玩家层面聚合信息。

这提供了玩家在整个比赛过程中行为的表示，而不仅仅是孤立事件周围的行为。

<a id="temporal-windows"></a>
### 时间窗口

时间窗口将连续观测分组，从而将短期行为表示为序列。

这对于瞄准移动等特征尤为重要，因为信号随时间的演变比单一测量更具信息量。

<a id="feature-storage"></a>
### 特征存储

生成的样本及其相关特征可以存储在可重用的数据集文件中。

目标是将昂贵的演示处理与后续机器学习实验分离，以便在不重新解析每个源比赛的情况下重复使用同一生成数据集。

完整的数据集构建会将每个处理过的比赛直接写入最终的CSV输出，而不是将所有先前处理过的比赛保留在内存中。这降低了在大规模构建过程中内存的峰值使用量。

每场完成的比赛后，都会更新一个轻量级检查点文件。如果构建过程被中断，可以使用 `--resume` 从断点处恢复，而无需重新构建之前已完成的比赛。如果在文件写入过程中发生中断，输出文件将被回滚到中断前比赛处理前记录的大小，然后重新处理该比赛。

<a id="missing-and-invalid-data"></a>
### 缺失和无效数据

数据管道会处理缺失或无效的值，以确保格式错误的样本不会静默地破坏生成的数据集。

这在处理来自不同来源的大量比赛集合时尤为重要。

<a id="numeric-normalization"></a>
### 数值归一化

数值特征可以被归一化为适合机器学习处理的一致表示形式。

归一化操作在数据集层面执行，而不是修改从源数据中提取的原始游戏行为信息。

<a id="labels"></a>
### 标签

数据集样本支持表示关联行为预期类别（包括正常和可疑数据）的标签。

标签层与特征提取层分离，以确保行为特征不直接编码预期结果。

<a id="dataset-splits"></a>
### 数据集划分

构建器会生成用于后续机器学习实验的训练、验证和测试划分。

一个核心要求是防止这些划分之间出现信息泄露。

因此，在分配样本时会考虑匹配情况和玩家身份，以确保当可用源数据允许时，高度相关的观测值不会被分散到训练和评估子集之间。

<a id="dataset-statistics"></a>
### 数据集统计

生成的数据集可以暴露其内容的统计信息。

这些统计信息提供了基本的验证步骤，用于在将样本用于模型训练之前检查生成样本的数量和分布情况。

<a id="external-dataset-support"></a>
## 外部数据集支持

M3 通过源特定适配器和一个标准的 CS2Guard 数据集表示形式引入了对外部数据集的支持。

首个被集成的外部数据源是 CS2CD。已实现专用适配器，并且其自动化测试均已通过。

关于 CS2CD 集成的详细决策，包括匿名玩家身份处理和数据泄露限制，详见 [`datasets/cs2cd.md`](datasets/cs2cd.zh-CN.md)。

<a id="cs2cd-identity-and-leakage-constraints"></a>
## CS2CD 身份与泄露限制

CS2CD 对玩家身份进行了匿名化，这使得 CS2Guard 无法直接将记录与原始演示文件中的 Steam 身份关联起来。

这意味着，玩家级别的数据泄露预防不能依赖于不同 CS2CD 匹配之间持久的现实世界玩家标识符。

因此，数据集管道必须保留源数据中可获得的最强分组信息，并记录数据泄露保证受限于源数据匿名化的位置。

这一区别非常重要，因为数据泄露预防是分割策略和源数据集提供的身份信息的双重属性。

<a id="coach--non-player-edge-case"></a>
## 教练/非玩家边缘情况

在M3验证期间，发现演示数据中存在一种边缘情况，即仅以教练身份出现的人。

教练可能出现在提取的与球员相关数据中，甚至可能产生类似游戏玩法的异常记录，例如在冻结时间期间死亡。

这意味着仅在解析输出中存在，并不足以保证该实体应被视为正常参与的玩家。

因此，在构建玩家级数据集时，必须保留该案例，以防止非参赛人员无意识地污染生成样本。

<a id="implementation-structure-1"></a>
## 实现结构

M3将项目从单个演示特征检查扩展为可重用的数据集流水线。

概念上：

```text
Demo files / external datasets
        ↓
src/cs2guard_demo/dataset/adapters/
        ↓
canonical CS2Guard data
        ↓
src/cs2guard_demo/features/
        ↓
dataset builder
        ↓
generated ML-ready datasets
```

源特定逻辑与标准数据集表示分离。这使得未来外部数据集可以通过其自身的适配器集成，而无需强制其余流程依赖其原始模式。

<a id="testing-2"></a>
## 测试

M3涵盖了数据集构建流水线和CS2CD适配器的自动化测试。

测试套件在不依赖大型本地演示集合的情况下独立验证数据集逻辑，而真实多演示构建则用于集成验证。

在M3结束时，自动化测试套件全部通过，包括专用的CS2CD适配器测试。

此外，已成功使用原生演示文件和CS2CD数据完成了一次大规模数据集构建。

最终的标准数据集包含：

* 2个数据源（`demo`和`cs2cd`）；
* 320场对局；
* 3,133名玩家；
* 523,083个事件；
* 229,149,465个时间步；
* 405,663个时间窗口；
* 405,663个瞄准特征样本。

此次大规模构建也验证了在实际数据体量下增量存储和检查点系统的有效性。

<a id="technical-decisions-1"></a>
## 技术决策

M3期间做出的重要决策包括：

* 通过可复现的数据集构建流水线处理多个对局；
* 支持事件级、玩家级和时间级表示；
* 将源数据摄入与标准CS2Guard数据集表示分离；
* 为外部数据集引入源特定适配器；
* 将CS2CD作为首个外部数据集集成方案；
* 保持特征提取与数据集标签的独立性；
* 以防止数据泄露为核心要求，生成训练、验证和测试划分；
* 当源数据提供充分的身份信息时，基于对局和玩家信息对样本进行分组；
* 在外部数据集匿名化身份时，明确记录较弱的玩家级数据泄露保证；
* 在数据集生成前处理缺失和无效样本；
* 暴露数据集统计信息以供验证；
* 将已完成的对局增量写入最终数据集文件，以避免在内存中累积全部源数据；
* 使用轻量级的每对局检查点和`--resume`机制，以应对长时间运行构建中断的情况。
* 在恢复中断的对局之前，回滚部分已写入的输出文件；
* 在确定有效玩家样本时，需考虑教练/非玩家的特例情况。

<a id="result-2"></a>
## 结果

M3 已完成并经过验证。

CS2Guard 现在能够将多个对局的数据转换为结构化、可重用的数据集，适用于后续的机器学习阶段。

演示分析器已从：

> ‘可以从一场对局中提取哪些行为特征？’

发展到：

> ‘这些特征如何转换为可复现的数据集，同时避免引入不可接受的数据泄露？’

项目现已具备后续模型训练和可疑行为检测所需的数据基础。

---

<a id="m4--anomaly-detection"></a>
# M4 — 异常检测

<a id="objective-3"></a>
## 目标

M4 的目标是构建第一个能够识别异常瞄准行为的机器学习检测器，而该检测器本身无需基于作弊标签进行训练。

M4 使用前几个里程碑生成的瞄准特征，并评估了多种无监督异常检测方法。

概念上：

```text
Aim feature samples
        ↓
Feature preprocessing
        ↓
Unsupervised anomaly detection
        ↓
Window / shot anomaly scores
        ↓
Player-level aggregation
        ↓
Initial suspicion score
```

CS2CD 的标签仅用于在生成异常分数之后进行评估和校准，不会作为输入特征提供给无监督模型。

<a id="input-features"></a>
## 输入特征

M4 使用了六个数值型瞄准特征：

* `mean_angular_speed`;
* `max_angular_speed`;
* `std_angular_speed`;
* `mean_angular_acceleration`;
* `max_angular_acceleration`;
* `std_angular_acceleration`.

标识符、源元数据和标签被排除在模型输入之外。

在模型实验之前，完整特征数据集已得到验证：

* 405,663 个瞄准特征样本；
* 六个模型特征中没有缺失值；
* 六个模型特征中没有无穷大值。

特征分布呈现强烈偏态，且包含合法的极端值，因此仅凭高速度或高加速度不能作为作弊的证据。

<a id="legitimate-behavior-baseline"></a>
## 合法行为基准

从 282,022 个标记为 `legitimate` 的窗口中建立了统计基准。

该合法基准包括每个瞄准特征的均值、标准差、中位数和上百分位数。

第 99 百分位数大约为：

* `mean_angular_speed`: 175.17;
* `max_angular_speed`: 692.76;
* `std_angular_speed`: 191.97;
* `mean_angular_acceleration`: 5,219.80;
* `max_angular_acceleration`: 25,087.75;
* `std_angular_acceleration`: 6,250.98.

合法样本仍可能大幅超出这些数值。因此，该基准被用作统计上下文，而非直接的作弊阈值集合。

<a id="isolation-forest"></a>
## 孤立森林

孤立森林被实现为首个异常检测的基准模型。

在推理前，六个特征会被标准化，模型输出：

* 一个窗口级别的异常分数；
* 一个二元异常预测；
* 一个玩家级别的聚合分数。

在完整数据集上：

* 窗口数量：405,663；
* 玩家-对局观测数量：3,138；
* 异常窗口数量：41,133。

在玩家层面，可疑玩家的平均异常分数高于合法玩家：

```text
legitimate mean   = -0.082159
suspicious mean   = -0.064996
```

这表明瞄准特征中存在可测量的异常信号，尽管两者之间的分离程度仍有限。

<a id="local-outlier-factor"></a>
## 局部异常因子

局部异常因子使用相同的标准化特征表示进行了评估。

在完整数据集上：

* 窗口数量：405,663；
* 玩家匹配观测值：3,138；
* 异常窗口数量：1,216。

LOF产生了高度不对称的原始分数。大多数窗口的LOF分数接近约1，而少数孤立样本获得了极高的分数。

在玩家层面：

```text
mean anomaly score

legitimate mean   = 266.428996
suspicious mean   = 494.548139

median

legitimate        = 1.038084
suspicious        = 1.049517
```

可疑玩家的异常窗口比例也更高：

```text
legitimate mean ratio   = 0.002257
suspicious mean ratio   = 0.007781
```

这些结果表明，可疑玩家表现出更多局部异常的瞄准行为，同时也证明了原始LOF值对少数极端样本非常敏感。

<a id="one-class-svm"></a>
## 单类支持向量机

还评估了使用RBF核的单类支持向量机。

为保持实验的计算可行性，模型在最多20,000个特征窗口的确定性样本上进行训练，然后用于对完整数据集进行评分。

基线使用：

```text
kernel = rbf
gamma = scale
nu = 0.05
```

在完整数据集上：

* 窗口数量：405,663；
* 玩家匹配观测值：3,138；
* 异常窗口数量：15,295。

在玩家层面，平均和中位数异常分数均对可疑玩家更高：

```text
                 mean       median
legitimate      -14.34      -16.01
suspicious       -7.97      -13.87
```

<a id="model-comparison"></a>
## 模型对比

在玩家层面使用ROC-AUC对三种方法进行了比较。

评估的玩家聚合方式为：

* `mean_anomaly_score`;
* `max_anomaly_score`;
* `anomalous_window_ratio`.

最佳结果为：

```text
LOF / mean_anomaly_score                ROC-AUC = 0.648464
Isolation Forest / mean_anomaly_score   ROC-AUC = 0.632018
One-Class SVM / mean_anomaly_score      ROC-AUC = 0.615009
```

完整对比显示，`mean_anomaly_score`在所有三种模型中表现最佳。

因此，LOF被保留作为最强的M4异常检测基线。

ROC-AUC仍然处于中等水平，因此M4并未证明仅靠异常检测足以实现可靠的作弊分类。

<a id="false-positive-analysis"></a>
## 误报分析

使用最异常的LOF窗口检查了得分最高的合法玩家。

一个常见模式是，仅有极少数窗口产生了极高的LOF分数。

这些窗口并不一定在任何单个特征上超过合法玩家的第99百分位。

这表明LOF主要检测的是瞄准特征的多变量组合异常，而非简单的单特征极端值。

这对解释具有重要限制：

```text
Anomalous behavior ≠ cheating
```

一个合法玩家可能占据特征空间中的局部稀疏区域，从而获得较高的异常分数。

<a id="feature-ablation"></a>
## 特征消减

通过逐个移除输入特征并重新计算LOF在玩家层面的ROC-AUC来评估特征影响。

基线：

```text
ROC-AUC = 0.648464
```

结果：

```text
Removed feature                  ROC-AUC    Baseline drop
std_angular_acceleration         0.642331    +0.006133
max_angular_acceleration         0.648252    +0.000212
max_angular_speed                0.649006    -0.000542
mean_angular_acceleration        0.649695    -0.001231
mean_angular_speed               0.652057    -0.003593
std_angular_speed                0.652337    -0.003873
```

`std_angular_acceleration`是本实验中最具影响力的单个特征。

然而，差异很小。因此M4保留所有六个特征，并将异常检测主要视为依赖于多变量特征组合，而非单一主导测量。

<a id="shot-level-anomaly-scores"></a>
## 单次射击层面的异常分数

每个时间序列瞄准窗口都以单次射击为中心。

LOF输出因此可以直接作为帧级异常分数暴露出来，同时通过`window_id`保持与原始时间窗口的关联。

生成的帧级输出包含：

* 405,663个评分帧事件；
* 405,663 个唯一窗口；
* 1,216个被LOF分类为异常的事件。

原始事件级LOF均值受到极端异常值的强烈影响。因此，事件评分对于定位异常瞄准序列是有用的，但玩家级聚合更适合用于初步怀疑分数。

<a id="player-level-anomaly-scores"></a>
## 玩家级异常分数

异常分数按比赛和玩家进行聚合。

玩家级输出包含：

* 分析的窗口数量；
* 异常分数均值；
* 异常分数最大值；
* 异常窗口比例。

完整数据集包含：

* 3,138 条玩家对战观测记录；
* 3,133 个唯一的 `player_id` 值；
* 1,801 条合法标注的玩家对战观测记录；
* 1,307 条可疑标注的玩家对战观测记录；
* 30 条来自原生演示数据的未标注玩家对战观测记录。

3,138 条玩家对战观测记录与 3,133 个唯一玩家 ID 之间的差异是预期的，因为某些玩家标识符会在多个对战层面的观测记录中出现。

<a id="initial-suspicion-score"></a>
## 初始怀疑分数

M4 引入了基于 LOF 平均异常分数的初始玩家怀疑分数。

由于原始 LOF 值可能变得极其庞大，因此未直接使用原始异常分数作为最终可解释的值。

相反：

```text
LOF mean anomaly score
        ↓
Percentile relative to legitimate players
        ↓
Suspicion score in [0, 100]
```

一个95的分数意味着该玩家的LOF平均异常分数高于大约95%的合法校准人群。

这并不意味着该玩家有95%的概率在作弊。

在标注数据集上：

```text
                 mean       median
legitimate       50.03       50.03
suspicious       64.85       73.74
```

一些合法玩家仍然获得接近100的分数，证实了怀疑分数不能被解释为作弊的证明，也不能作为自动执行的阈值。

<a id="implementation-structure-2"></a>
## 实现结构

M4引入了异常检测层：

```text
src/cs2guard_demo/detection/
        ↓
feature preprocessing
        ↓
Isolation Forest / LOF / One-Class SVM
        ↓
window / shot anomaly scores
        ↓
player aggregation
        ↓
suspicion score
```

支持脚本提供：

* 合法基线分析；
* 异常模型执行；
* 模型对比；
* 误报检查；
* 特征消减；
* 怀疑分数生成；
* 每回合异常分数生成。

<a id="testing-3"></a>
## 测试

M4由自动化测试覆盖：

* 孤立森林执行；
* 局部异常因子执行；
* 用于特征消减的LOF特征子集；
* 一类支持向量机执行；
* 缺失特征验证；
* 无效数值特征验证；
* 怀疑分数生成。

在M4结束时，完整的自动化测试套件全部通过。

三个异常检测模型也在完整的405,663窗口数据集上进行了执行。

<a id="technical-decisions-2"></a>
## 技术决策

M4期间做出的重要决策包括：

* 仅使用行为目标特征作为无监督模型的输入；
* 将标识符、源元数据和标签排除在异常模型特征之外；
* 仅将CS2CD标签用于评估和校准；
* 在异常检测实验前对特征进行标准化；
* 比较孤立森林、局部异常因子和一类支持向量机；
* 在确定性样本上训练一类支持向量机，以使实验在计算上可行；
* 使用ROC-AUC进行跨模型比较，因为原始异常分数尺度差异显著；
* 在玩家层面评估分数，而不是将每个时间窗口视为独立的玩家；
* 保留局部异常因子作为最强的M4基线，其玩家层面的ROC-AUC为0.648464；
* 在消融分析后保留所有六个目标特征，因为单个特征的影响较小；
* 将高异常分数视为异常行为，而非直接的作弊证据；
* 将时间窗口分数转换为每发子弹事件的分数；
* 将局部异常因子的玩家分数转换为初始0–100怀疑分数的合法相对百分位；
* 在M4期间避免设定封禁或作弊分类阈值。

<a id="result-3"></a>
## 结果

M4已完整并经过验证。

CS2Guard现在可以为单发目标事件分配异常分数，并将这些信号聚合为玩家层面的异常和怀疑分数。

在评估的无监督方法中，局部异常因子在玩家层面表现出最强的分离效果：

```text
ROC-AUC = 0.648464
```

结果表明，可疑与合法玩家在当前目标特征空间中表现出可测量的差异，但这种分离程度尚不足以将异常检测视为独立的作弊分类器。

演示分析器已从：

> "行为特征如何转化为可复现的数据集？"

发展到：

> "能否自动检测异常瞄准行为，以及如何将这些证据聚合为可解释的玩家层面怀疑信号？"

M4为M5计划中的监督实验提供了异常检测基线。

---

<a id="m5--supervised-detection"></a>
# M5 — 监督检测

<a id="objective-4"></a>
## 目标

M5的目标是在通过标准数据集获得可靠的合法与可疑标签后，评估监督分类方法。

M5复用M4期间评估的相同六个瞄准特征，但与异常检测不同，监督模型是明确使用可用的CS2CD标签进行训练的。

概念上：

```text
Labeled aim features
        ↓
Leakage-safe train / test split
        ↓
Supervised classification
        ↓
Model evaluation
        ↓
Hyperparameter tuning
        ↓
Threshold analysis
        ↓
Player-level suspicion scores
```

M5的一个核心要求是保持训练数据和评估数据之间的比赛层面隔离，以确保同一场比赛中的窗口不会同时出现在两个数据集中。

<a id="labeled-dataset"></a>
## 标注数据集

从标准瞄准特征数据集中生成一个专用的监督数据集。

仅保留具有有效标签的样本：

```text
legitimate
suspicious
```

未标注的原生演示样本被排除在监督训练之外。

监督数据集包含：

* 397,487个标注样本；
* 317个匹配项；
* 3,108名玩家；
* 6个数值目标特征。

标签分布为：

```text
legitimate    282,022
suspicious    115,465
```

六个模型特征与M4中使用的相同：

* `mean_angular_speed`;
* `max_angular_speed`;
* `std_angular_speed`;
* `mean_angular_acceleration`;
* `max_angular_acceleration`;
* `std_angular_acceleration`.

如`match_id`、`player_id`、`window_id`以及标签本身作为数据集管理与评估的标识符被保留，但不会作为模型输入提供。

<a id="train--test-split"></a>
## 训练/测试划分

监督数据集采用匹配级别分组进行划分。

并非将单个窗口随机分配到训练集和测试集中，而是属于同一匹配的所有样本保留在同一分区中。

这防止了模型在训练时使用到测试集中被保留的匹配项中的窗口。

固定划分使用：

```text
Train
306,315 samples
253 matches

Test
91,172 samples
64 matches
```

训练集标签分布为：

```text
legitimate    215,434
suspicious     90,881
```

测试集标签分布为：

```text
legitimate     66,588
suspicious     24,584
```

该划分使用固定随机种子，以确保所有M5实验均使用相同的保留匹配项进行评估。

<a id="baseline-classifiers"></a>
## 基线分类器

M5首先建立了两个基线分类器。

<a id="dummy-classifier"></a>
### 伪分类器

使用训练集类别先验的`DummyClassifier`提供了一个简单的参考基准。

在保留的测试集上：

```text
accuracy = 0.7304
```

在默认决策规则下，模型预测无可疑样本：

```text
Precision = 0.0000
Recall    = 0.0000
F1-score  = 0.0000
ROC-AUC   = 0.5000
PR-AUC    = 0.2696
FPR       = 0.0000
```

PR-AUC对应于保留测试集中正类的占比，因此为后续模型提供了有用的基准参考。

<a id="logistic-regression"></a>
### 逻辑回归

逻辑回归被用作第一个学习型监督基线分类器。

该分类器被置于一个`StandardScaler`内部的scikit-learn管道中，以确保特征缩放仅在训练数据上拟合。

初始结果为：

```text
accuracy  = 0.7306
Precision = 0.5102
Recall    = 0.0214
F1-score  = 0.0410
ROC-AUC   = 0.5547
PR-AUC    = 0.3230
FPR       = 0.0076
```

准确率几乎与伪分类器基线相同，而召回率仍极低。

这说明了为何仅凭准确率不足以评估反作弊分类问题。

<a id="random-forest"></a>
## 随机森林

随机森林被引入作为第一个非线性监督模型。

初始配置使用：

```text
n_estimators     = 100
max_depth        = 20
min_samples_leaf = 5
```

初始保留结果为：

```text
accuracy  = 0.7340
Precision = 0.5336
Recall    = 0.1078
F1-score  = 0.1794
ROC-AUC   = 0.5933
PR-AUC    = 0.3813
FPR       = 0.0348
```

随机森林在召回率、F1分数和PR-AUC方面显著优于逻辑回归，表明目标特征之间的非线性交互包含有用的监督信息。

<a id="histogram-gradient-boosting"></a>
## 直方图梯度提升

`HistGradientBoostingClassifier`被评估作为第二个非线性监督模型。

它被选中而非经典`GradientBoostingClassifier`，因为基于直方图的实现更适合M5使用的约30万训练样本。

初始配置使用：

```text
learning_rate  = 0.1
max_iter       = 100
max_leaf_nodes = 31
```

初始保留结果为：

```text
accuracy  = 0.7356
Precision = 0.5593
Recall    = 0.0915
F1-score  = 0.1572
ROC-AUC   = 0.5934
PR-AUC    = 0.3791
FPR       = 0.0266
```

初始梯度提升模型在精确率和假阳性率方面略高于初始随机森林，而随机森林在召回率、F1分数和PR-AUC方面表现更优。

<a id="evaluation-metrics"></a>
## 评估指标

M5为所有监督模型引入了一个通用的评估层。

评估的指标包括：

* 精确率；
* 召回率；
* F1分数；
* ROC-AUC；
* PR-AUC；
* 假阳性率；
* 混淆矩阵计数。

可疑类别被视为正类：

```text
0 = legitimate
1 = suspicious
```

PR-AUC 使用平均精度而非直接对精确率-召回率曲线进行梯形积分实现。

这确保了常数分数分类器产生的基准值对应于正类的普遍程度。

对于保留的测试数据集：

```text
positive prevalence ≈ 0.2696
```

因此，Dummy 分类器产生：

```text
PR-AUC = 0.2696
```

<a id="hyperparameter-tuning"></a>
## 超参数调优

随机森林和直方图梯度提升使用随机搜索进行调优。

保留的64个匹配测试集在超参数选择过程中未被使用。

相反，调优仅在253个训练匹配上使用分组交叉验证进行。

概念上：

```text
253 training matches
        ↓
StratifiedGroupKFold
        ↓
3 validation folds
        ↓
PR-AUC optimization
        ↓
Best hyperparameters
```

PR-AUC / 平均精度被用作主要调优指标，因为可疑样本比合法样本更少，且对可疑行为进行排序比单纯准确率更有信息量。

<a id="random-forest-tuning"></a>
### 随机森林调优

最佳随机森林交叉验证结果是：

```text
Best CV PR-AUC = 0.4471
```

其中：

```text
n_estimators     = 150
min_samples_leaf = 5
max_features     = sqrt
max_depth        = 15
class_weight     = None
```

<a id="histogram-gradient-boosting-tuning"></a>
### 直方图梯度提升调优

最佳直方图梯度提升结果是：

```text
Best CV PR-AUC = 0.4457
```

其中：

```text
max_leaf_nodes    = 63
max_iter          = 150
learning_rate     = 0.1
l2_regularization = 1.0
class_weight      = balanced
```

在分组交叉验证过程中禁用了内部早停，以防止额外的随机验证分割重新引入匹配级别的信息泄露。

随机森林在交叉验证PR-AUC上表现略优，并被保留为主要M5监督模型候选。

<a id="tuned-model-evaluation"></a>
## 调优模型评估

调优后，两个选定配置均在完整的253个匹配训练集上重新训练，并在保留的64个匹配测试集上进行一次评估。

<a id="tuned-random-forest"></a>
### 调优的随机森林

调优后的随机森林产生：

```text
Precision = 0.5669
Recall    = 0.0929
F1-score  = 0.1596
ROC-AUC   = 0.5932
PR-AUC    = 0.3818
FPR       = 0.0262
```

与未调优的随机森林相比，调优模型变得更加保守：

```text
Precision increases
FPR decreases
Recall decreases
```

<a id="tuned-histogram-gradient-boosting"></a>
### 调优的直方图梯度提升

调优后的直方图梯度提升模型产生：

```text
Precision = 0.3437
Recall    = 0.4488
F1-score  = 0.3893
ROC-AUC   = 0.5950
PR-AUC    = 0.3827
FPR       = 0.3164
```

平衡类权重显著提高了可疑样本的召回率，但这也带来了更大的假阳性率。

这表明，一个具有有用排序分数的模型并不一定具有适当的默认分类阈值。

<a id="false-positive-and-threshold-analysis"></a>
## 假阳性与阈值分析

因此，M5在多个概率阈值上评估调优模型。

分析的阈值范围从：

```text
0.10
to
0.90
```

对于每个阈值，CS2Guard测量：

```text
precision
recall
F1-score
false-positive rate
false positives
true positives
```

分析展示了预期的权衡：

```text
lower threshold
    ↓
higher recall
    ↓
more false positives

higher threshold
    ↓
lower false-positive rate
    ↓
lower recall
```

例如，调优后的随机森林在阈值`0.50`下产生：

```text
Precision = 0.5669
Recall    = 0.0929
F1-score  = 0.1596
FPR       = 0.0262
```

调优后的直方图梯度提升模型在阈值`0.70`附近达到相似的假阳性区域：

```text
Precision = 0.5666
Recall    = 0.0967
F1-score  = 0.1652
FPR       = 0.0273
```

相比之下，其默认阈值`0.50`产生：

```text
Recall = 0.4488
FPR    = 0.3164
```

这表明，当前要实现显著更高的召回率，需要不可接受的假阳性增加。

在M5阶段，并未最终确定任何执行或作弊分类阈值。

预留的测试集用于表征模型行为，而不是反复优化生产阈值。

<a id="supervised-vs-anomaly-detection"></a>
## 监督学习与异常检测

M5还引入了直接的预留对比，将监督学习与M4阶段开发的异常检测方法进行比较。

原始M4实验与监督M5的事件级指标不可直接比较，因为它们采用了不同的评估条件和聚合层级。

因此采用了一种新的通用评估方法：

```text
same 253 training matches
same 64 held-out test matches
same six aim features
same player-match aggregation
```

局部异常因子在新颖模式下进行评估。

它仅在训练特征上进行拟合，然后用于对预留样本进行打分，拟合过程中不使用作弊标签。

随后，将监督事件概率和LOF异常分数按对局和玩家进行聚合。

该通用预留评估包含：

```text
637 player-match observations
```

结果为：

```text
Random Forest tuned
ROC-AUC = 0.7779
PR-AUC  = 0.6840

HistGradientBoosting tuned
ROC-AUC = 0.7798
PR-AUC  = 0.6800

LOF held-out
ROC-AUC = 0.6323
PR-AUC  = 0.4624
```

因此，监督方法在当前标注的瞄准特征数据集上显著优于预留LOF基线。

随机森林与梯度提升树的性能仍然非常接近。

随机森林被保留为M5的主要模型，因为它在分组交叉验证中取得了最佳PR-AUC，并且在玩家级预留PR-AUC上达到了最高水平。

这一结果并不意味着异常检测已经过时。

当标签不可用时，无监督打分仍然可以保持有用，例如用于探索性分析，或作为后续怀疑分数聚合中的额外信号。

<a id="model-persistence-and-versioning"></a>
## 模型持久化与版本管理

M5为训练好的监督模型引入了持久化功能。

所选的随机森林可以保存为一个版本化的模型包：

```text
models/supervised/
├── random_forest_v1.joblib
└── random_forest_v1.json
```

`.joblib`文件包含训练好的scikit-learn模型。

JSON元数据记录了用于识别和重现模型所需的信息，包括：

* 模型名称；
* 版本；
* 输入特征；
* 标签映射；
* 超参数；
* 随机种子；
* 训练样本和对局数量；
* 预留测试样本和对局数量；
* 事件级评估指标；
* 玩家级ROC-AUC和PR-AUC。

模型元数据保持：

```text
decision_threshold = None
```

因为M5并未选定最终的运行阈值。

因此，该模型主要被持久化为一个概率性怀疑打分模型，而非自动作弊执法分类器。

<a id="implementation-structure-3"></a>
## 实现结构

M5引入了一个专门的监督学习层：

```text
src/cs2guard_demo/supervised/
        ↓
dataset preparation
        ↓
baseline / RF / HGB models
        ↓
evaluation
        ↓
hyperparameter tuning
        ↓
threshold analysis
        ↓
supervised / anomaly comparison
        ↓
model persistence
```

主要实现职责被划分为：

```text
dataset.py
    → labeled dataset preparation and grouped splitting

models.py
    → supervised model definitions and training

evaluation.py
    → classification metrics and threshold analysis

tuning.py
    → grouped hyperparameter search

comparison.py
    → player-level supervised / anomaly comparison

persistence.py
    → model and metadata serialization
```

支持脚本提供：

* 标注数据集生成；
* 基线和模型训练；
* 超参数调优；
* 调优模型评估；
* 阈值分析；
* 监督与异常检测对比；
* 模型持久性。

<a id="testing-4"></a>
## 测试

M5扩展了自动化测试套件以覆盖：

* 标注数据集构建；
* 无效标签和数值；
* 对局级训练 / 测试隔离；
* 监督特征和目标准备；
* 基线分类器创建与训练；
* 随机森林创建与训练；
* 直方图梯度提升创建与训练；
* 调优模型创建与训练；
* 精确率、召回率、F1分数、ROC-AUC和PR-AUC评估；
* PR-AUC在恒定分类器下的行为；
* 可配置阈值评估；
* 无效阈值处理；
* 阈值分析；
* 对局互不重叠的分组交叉验证；
* 随机森林调优；
* 直方图梯度提升调优；
* 玩家层面分数聚合；
* 在留出集上进行 LOF 评分；
* 监督与异常检测对比；
* 模型持久性与重新加载行为。

M5的监督测试套件在最后阶段通过。

实际实验也在完整的标注数据集和固定的保留匹配划分上执行过。

<a id="technical-decisions-3"></a>
## 技术决策

M5期间做出的重要决策包括：

* 复用 M4 的六个瞄准特征，确保监督学习与异常检测实验具有可比性；
* 将未标注样本排除在监督训练之外；
* 在分组时保留标识符，但在模型输入中排除标识符；
* 按匹配而非单个窗口划分训练和测试数据；
* 整个 M5 阶段固定使用由 64 场对局构成的留出测试集；
* 仅在训练数据上拟合预处理；
* 使用DummyClassifier作为性能基准的简单模型；
* 使用逻辑回归作为首个学习到的监督基线模型；
* 将随机森林和直方图梯度提升作为非线性表格模型进行评估；
* 使用精确率、召回率、F1分数、ROC-AUC和PR-AUC，而非依赖准确率；
* 使用平均精确率来计算PR-AUC；
* 使用分组交叉验证进行超参数调优；
* 使用PR-AUC而非准确率来优化超参数；
* 在分组调优过程中禁用直方图梯度提升的内部早停机制；
* 将决策阈值与模型排序性能分开分析；
* 将假阳性率视为关键反作弊评估指标；
* 避免从保留测试集中选择生产执行阈值；
* 在相同留出对局上比较监督学习和无监督方法，并采用相同的玩家级聚合；
* 保留随机森林作为M5主要的监督模型；
* 保留直方图梯度提升作为可靠的替代模型；
* 将选定模型与用于复现的元数据一同持久化；
* 持久化的 M5 模型不绑定决策阈值，由后续 Demo Analyzer 逻辑确定分数如何聚合与解释。

<a id="result-4"></a>
## 结果

M5已完整并经过验证。

CS2Guard现在可以使用标注的瞄准特征数据训练、调优、评估和持久化监督性行为分类器。

初步的事件级结果表明，当每个以射击为中心的窗口被独立处理时，分类仍然具有挑战性。

然而，在保留的测试集中进行玩家级聚合则产生了显著更强的区分能力。

主要的M5随机森林达到了：

```text
ROC-AUC = 0.7779
PR-AUC  = 0.6840
```

玩家-对战级别。

相比之下，保留的局部异常因子达到了：

```text
ROC-AUC = 0.6323
PR-AUC  = 0.4624
```

这表明可用的作弊标签提供了超越纯无监督异常检测的大量额外信息。

与此同时，阈值分析证实，检测性能与误报控制始终处于矛盾之中。

因此，监督模型被视为行为可疑性的证据来源，而非证明某玩家在作弊的依据。

Demo Analyzer已从：

> "是否可以自动检测到异常的瞄准行为？"

发展到：

> "标注的行为数据是否能提升可疑玩家的排序，以及由此生成的模型能否在不引入可避免的数据泄露的前提下被评估和持久化？"

M5为M6中的离线Demo Analyzer提供了所使用的监督模型。

---

<a id="m6--demo-analyzer"></a>
# M6 — Demo Analyzer

<a id="initial-audit-scope-and-reference-state--2026-10-14"></a>
## 初始审计范围和参考状态 — 2026-10-14

2026-10-14的审计与实施保留了README路线图：M6是离线演示分析。服务器端流处理仍为M9/M10；`server_side/`保持不变。初始分支为`main`，且无本地跟踪变更。项目采用setuptools布局`src`和标准导入`cs2guard_demo`。所有Python源码、20个历史脚本、测试用例、包/测试配置、架构文档以及持久化的M5元数据均已检查。模型构件、数据集和研究成果均被保留。

现有的`.venv`使用Python 3.13.1、pytest 9.1.1、NumPy 2.5.2、pandas 3.0.5、scikit-learn 1.9.1、demoparser2 0.42.0、Matplotlib 3.11.1和joblib 1.6.0。系统Python缺少demoparser2；因此命令使用项目环境。已安装的持久化模型是一个包含150棵树的RandomForestClassifier，其类为`[0, 1]`，且包含训练顺序中的六个预期特征名称。其加载时无兼容性警告。模型和JSON文件均保持不变。

在任何代码变更之前的基准是 **179项通过，0项失败，0项跳过**。此前的默认沙箱运行结果为 **163项通过和16个测试环境设置错误**，这是由于系统临时目录不可访问，而非应用故障。一个本地仓库的`--basetemp`建立了干净的基准。此临时方案后来在用户请求下被移除；最终测试使用原生pytest系统临时目录并获得批准的文件系统访问权限。

<a id="confirmed-audit-findings-and-actions"></a>
## 确认的审计发现与行动

本表中的路径相对于`demo_analyzer/`，除非另有说明。

|文件 / 符号|问题|证据|行动|风险|
|---|---|---|---|---|
| `src/cs2guard_demo/parser/events.py`, `utils/logger.py` |死板占位符|空文件，无Python/文档引用，无导出实现|仅删除了这两个文件|低|
|`parser/demo_parser.py` pandas导入；`scripts/parse_demo.py`，`visualize_aim.py` `ROOT_DIR`|未使用导入/变量|AST和引用检查仅显示声明|已移除|低|
|`DemoParser` 发射/命中/击杀/计时/玩家/团队/回合|空后端帧引发`KeyError`|后端受控返回`DataFrame()` 且无列|保留空输出模式/列表|低；非空行为未改变|
| `DatasetBuilder.build_temporal_windows`, `build_canonical_temporal_windows` |重复的发射/计时行会破坏窗口|重复的发射会重复一个`window_id`；重复的计时可满足行数但不完整时间线|去重发射，拒绝模糊的计时窗口|中等；无效/重复输入行为故意修正|
|相同的窗口构建器|重复的完整计时扫描|每个发射过滤整个计时帧|一次分组和排序，使用`searchsorted`选择边界|低；精确功能结果已测试|
| `dataset/builder.py`, `dataset/adapters/demo.py` |无穷大替换在安装的pandas中崩溃|回归测试用例重现`IndexError: pop index out of range`与`pd.NA`|在现有排除前将无穷大替换为NaN|低；排除语义保持不变|
| `dataset/adapters/cs2cd.py` |无穷大遥测数据在归一化后仍存在|合成的NaN/Inf数据|移除无效的必需遥测数据|低|
| `scripts/build_dataset.py::append_dataframe` |CSV头在不同源间不同；空块影响后续头|Demo/CS2CD测试用例中可选字段和顺序不同|稳定现有字段的合并，跳过空块，拒绝未知字段/不兼容的恢复头|中等；旧版中断的CSV可能需要重建|
| `scripts/build_dataset.py::build_demo_chunk/build_cs2cd_chunk` |相同的特征流水线|仅适配器构造不同|重用`build_chunk(builder, adapter)`|低|
| `dataset/statistics.py::generate_dataset_statistics` |标准数据集玩家数量为零|函数仅读取`steamid`，该字段在标准模式中不存在|优先使用`player_id`，保留旧版后备|低|
| `dataset/labels.py`, `statistics.py`, `detection/anomaly.py`, `scripts/analyze_false_positives.py` |标签重复/六特征列表重复|多个模块中常量相同|导入现有模式/归一化常量|低；顺序已检查|
| `scripts/validate_demo.py` |空窗口引发`KeyError: window_id`|测试运行实际脚本`main()`并使用空数据|重用条件窗口计数|低|
| `supervised/comparison.py::aggregate_player_scores` |系列按无关的pandas索引对齐|数据集索引`[10,11]`，分数索引`[0,1]`产生NaN|位置赋值`np.asarray(scores)`|低；ndarray脚本未改变|
| `supervised/evaluation.py::evaluate_predictions` |单类目标返回未定义指标|单类ROC-AUC/FPR产生NaN|显式错误，除非同时存在0/1类|较低；历史指标有效且未改变|
| `scripts/train_supervised.py`, `evaluate_tuned_supervised.py::print_metrics` |指标打印完全一致|相同字段/格式|复用现有评估模块函数|较低；输出已验证|
| `visualization/aim.py::plot_aim_trajectory` |M6无保存输出|图表关闭但未导出|可选`output_path`和`distance_label`；默认行为不变|较低|
|M1至M5测试用例|真实重复工作|事件测试重复精确的多演示场景；探测器/训练测试重复设置/断言|合并事件断言；参数化模型用例|较低；独立覆盖保留|

以下相似性已审查并**保留**，而非视为确认的死代码：

|符号 / 家族|保留原因|
|---|---|
|遗留DatasetBuilder事件/窗口API与DemoAdapter标准API|身份方案、输出结构和公开调用者不同；合并将引入转换|
|M4与M5玩家聚合|M4使用六个身份键及均值/最大值/异常比率；M5使用匹配/玩家及均分得分|
|转导式M4 LOF与预留M5新颖性LOF|不同的评估任务；持有路径中的仅训练缩放器至关重要|
|M2获取/跟踪/反应/修正/快照辅助函数|公开导出、独立测试行为及实验可视化调用函数|
|历史脚本和持久化研究成果|不同的实验、文档化使用和可重现价值|
|相似的适配器测试框架|源格式和归一化责任不同|
|完整的解析器玩家名单，包括可能的预热参与者|历史语义可能有用；M6保留玩家并标记缺席证据，而非静默丢弃|

科学公式、角度封装、时钟单位、总体标准差（`ddof=0`）、缩放器拟合、特征排序、模型参数、分组分割、LOF得分符号和ECDF校准在有效历史数据中保持不变。未引入任何生产阈值或新校准。无效的重复/非有限窗口和未定义指标现在明确失败或被排除。

<a id="coverage-and-test-consolidation"></a>
## 覆盖范围和测试整合

|功能区域|覆盖范围已检查|之前|之后|
|---|---|---:|---:|
|M1解析器|有效归一化数据包、玩家/事件/轮次/时钟、最新比赛开始、缺失文件、后端错误、空数据、带/不带时钟的比赛| 7 | 14 |
|M2几何结构和图表|±180°封装、方向/距离、速度/加速度/时间、获取/响应、跟踪/修正/超调/快照、射门关联、无效输入、真实PNG导出| 95 | 96 |
|M3数据集/适配器/脚本|标准ID/标签、多匹配窗口、有限数据、精确数值特征、不规则tick时间、重复/不完整窗口、归一化、无匹配泄漏的分割、统计分析、稳定的CSV文件/恢复回滚| 42 | 61 |
|M4异常|IF/LOF/OCSVM训练/评分、特征排序/类型转换、有限值、评分方向、可复现性、身份聚合、ECDF平局/校准错误| 7 | 18 |
|M5监督学习|基线/随机森林/HGB/调优模型、有限归一化概率值、分组交叉验证/分割可复现性、阈值、指标、玩家均值、位置得分、预留LOF、持久性与特征顺序| 28 | 46 |
|M6分析|端到端M1–M5集成控制、全玩家阵容、精确均值/排名、轮次/事件、图表/报告、模型兼容性、部分/空数据、精确树贡献和命令行接口| 0 | 39 |
|**总计**|**无跳过测试**| **179** | **274** |

M1–M5增益**57个案例**，移除**一个精确重复项**，合并后共**235个案例**。`test_event_level_samples`合并至`test_process_multiple_demos`，保留所有断言。三个探测器测试合并为一个覆盖相同三个探测器的参数化测试；四个训练测试合并为一个覆盖相同四个路径的参数化测试。M6在`test_analysis.py`中新增39个案例。`test_build_dataset_script.py`是唯一新增的测试文件。原有的91个M2特征测试被保留；外观相似的案例实际覆盖不同的算法或边界条件。

新测试首次暴露出pandas无穷大崩溃和标准玩家统计缺失问题；这两个问题均已修复并验证。新增的随机森林持久性断言最初使用精确相等判断，在`1.11e-16`处失败；现在`1e-12`引入容差以应对并行浮点树求和。添加显式部分数据计数器后，两个M6的预期值被更新。没有历史成功的测试被削弱以掩盖产品回归问题。

自动化测试仍保持小型且合成性质。没有测试套件需要下载演示版本、外部CS2CD数据或昂贵的全数据集训练。CS2CD匿名化仍无法保证不同对局间真实玩家的互斥性；对局级互斥性已被测试。本次初步审计未重复历史全数据集模型实验。

<a id="implementation-and-scientific-interpretation"></a>
## 实现与科学解释

初始M6实现引入了`analysis.py`、`cli.py`和`__main__.py`；`pyproject.toml`注册了`cs2guard = cs2guard_demo.cli:main`。Matplotlib，已在M2中使用并安装，现被声明为运行时依赖，因为报告需要它。现有环境初始缺少setuptools构建支持，阻碍了无构建隔离安装；普通隔离构建仅安装项目已声明的构建依赖。未引入额外的建模、报告或命令行接口依赖。

流水线复用DemoAdapter/DemoParser、DatasetBuilder、M2几何/图表、M4 `prepare_features`、M5捆绑加载和M5玩家聚合。它检查非空`.dem`输入、相邻元数据、特征名称/顺序/维度、类别映射、概率输出形状/范围以及可选的记录提取设置。分析过程中从不拟合模型。历史提取设置固定为32个tick和64Hz，与训练脚本一致；缺失的元数据设置被明确记录为兼容性限制。

每一个解析器-阵容球员、遥测/事件参与者以及事件受害者均被保留。对于没有有限完整射窗的球员，其得分为空值并附带解释。拥有射窗的球员按M5均值从高到低排序，然后按标准ID排序；未得分的球员在之后按顺序排列且不赋予排名。完整的JSON保留了每一个得分射窗以及六个测量特征。轮次关联使用射击时间步；若缺乏完整轮次上下文，则保持为空，并标记跨越射窗的情况。在相同参与者/武器/轮次的接下来两个时间步内发生的事件提供邻近检查上下文，而非证明射击与命中之间因果关系的证据。

每个球员中得分最高的三个射窗被选中用于检查，即使所有得分都很低。这仅是显示限制，而非经过验证的怀疑阈值。轮次检查优先级是每个完整轮次中最高得分的射窗，而非校准过的轮次概率。速度和加速度指标是射窗特征均值的算术平均值，单位为度/秒和度/秒²；它们不与模型输出结合。当观测到受害者同时具有遥测数据时，跟踪测量仅使用M2；否则，图示明确引用射击瞄准方向。反应阶段没有观测到的视觉刺激，因此始终不可用。全局RF特征重要性和原始射窗值解释了可用的测量结果。对于持久化的M5 RF和原生决策树，局部贡献也分解了现有预测：每个分裂贡献其特征上子节点减父节点的类别1概率。根基准值加上这些带符号的变化项相加后得到叶节点概率。变化和基准值在森林树之间取平均；球员贡献在射窗之间取平均，与M5得分聚合完全一致。输入转换使用与scikit-learn树推理相同的float32精度。重构被声明在容差`1e-12`内。这仅是对未改变模型的算术解释，而非新的检测器或校准。它依赖于分裂顺序，既不是因果归因，也不是SHAP。不支持的估计器家族明确保留空的局部贡献；其测量特征和全局重要性保持独立。不存在新的行为异常子模型、任意加权得分、未标记球员上的ECDF校准或作弊结论。

`report.json`是机器可读的；`report.md`提供排名、行为值、轮次优先级、审核序列边界/事件/特征、图像链接和解释限制。CLI退出码0表示至少有一个球员有得分；可用的部分分析被明确标记为`partial`。`complete`要求每个阵容球员都有射窗，所有符合条件的射击都必须得分，且不存在缺失或跨越的轮次上下文。`partial`在保留可用得分的同时暴露这些缺失；`insufficient_data`表示没有任何球员可以被评分。退出码2表示输入无效、模型缺失或不兼容、解析或输出失败，或没有得分射窗。无数据报告保留空值得分，而非伪造的零值。

<a id="reproducible-validation"></a>
## 可复现的验证

《[README 快速入门](../README.zh-CN.md#quick-start)》涵盖了Python 3.11+的安装和基本分析。详细的接受协议在此保留；README保留了十一项M6检查清单内容。

推理需要一个可信的M5 `.joblib`包及其相邻的`.json`元数据；模型字节和演示文件被Git忽略，并且在新的克隆中不会包含。安装和自动化测试都不需要。如果必须单独构建包，则历史命令如下，它从现有的`demo_analyzer/data/processed/supervised_dataset.csv`中训练M5；这不包含在推理中：

```powershell
Set-Location demo_analyzer
..\.venv\Scripts\python.exe scripts/save_supervised_model.py
Set-Location ..
```

从仓库根目录执行的命令：

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps --disable-pip-version-check -e .
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q demo_analyzer/src demo_analyzer/scripts demo_analyzer/tests
.\.venv\Scripts\python.exe -c "import cs2guard_demo.analysis, cs2guard_demo.cli, cs2guard_demo.parser, cs2guard_demo.dataset, cs2guard_demo.detection, cs2guard_demo.supervised, cs2guard_demo.visualization; print('Imports: OK')"
.\.venv\Scripts\cs2guard.exe analyze --help
.\.venv\Scripts\python.exe -m cs2guard_demo --help
.\.venv\Scripts\cs2guard.exe analyze demo_analyzer/data/raw/train_sources/demo/test.dem --model demo_analyzer/models/supervised/random_forest_v1.joblib --output demo_analyzer/data/processed/m6_validation
git diff --check
```

初始审计套件：**274项通过，0项失败，0项跳过**。`pip check`、语法编译、标准导入和命令行帮助均通过。所有 **75个Python文件** 均可解析；**26个非命名空间实现模块** 和 **20个脚本** 成功导入。未配置任何语法检查或类型检查工具。历史训练脚本通过库测试覆盖，而非在完整数据集上执行。它们保留了预期的`demo_analyzer/`工作目录和数据前提条件。多源构建器的帮助和回滚/头部路径被测试，而不会覆盖研究数据集。

<a id="initial-acceptance-protocol"></a>
### 初始接受协议

自动化检查已通过受控解析器、实际的M1–M5代码、一个小型持久分类器和真实的PNG输出，覆盖了全部十一项README标准。五个测试玩家保持存在；不可用的分数为null。测试结果和玩家均值一致，无效模型/输入情况被拒绝，平局或输入顺序调整后保留了排名。轮次边界、未知关联、边界标志以及三窗口显示限制均与测试结果一致。

RF/树基线加上带符号的贡献，重构了窗口/玩家得分，位于`1e-12`内。保存的JSON与返回数据匹配；Markdown图像链接解析成功，PNG文件是非恒定的，物理单位和不可用指示器保持明确。命令行帮助和评分功能成功；无效输入、缺失模型和得分为零的窗口退出状态码2。这些检查保留在`test_analysis.py`和`test_aim_visualization.py`中；上述命令通过完整套件运行它们。

初始真实运行仅使用了方向参考。以下记录的结果保留了该证据；在后续的鲁棒性审计中展示了观察到的受害者图。

<a id="real-local-demo"></a>
### 真实本地演示

已安装的`cs2guard`命令实际上在`demo_analyzer/data/raw/train_sources/demo/test.dem`（312,377,735字节）上运行，M5 RF包保持不变。在实现过程中重复进行分析；显示的玩家均值和排名在小数点后六位一致。最终报告状态为**部分**，因为部分窗口缺乏完整轮次上下文或跨越边界；但所有十名玩家均拥有分数。

|记录项|结果|
|---|---:|
|玩家 / 得分玩家| 10 / 10 |
|归一化遥测行| 1,624,992 |
|归一化事件| 2,966 |
|评分的32步窗口| 2,272 |
|完成的轮次| 21 |
|未评分的合格射门| 0 |
|无完成轮次关联的窗口| 42 |
|跨越轮次边界的窗口| 36 |
|保存的PNG审查图| 30 |
|最高 / 最低玩家均值| 0.263435 / 0.237090 |

每个玩家的保存分数都会与其保存窗口分数的平均值进行比对，容差为`1e-12`。根基准线加上带符号路径贡献项也会与全部2,272个RF窗口概率进行比对；最大误差为`4.44e-16`。保存的JSON贡献项能够重构全部2,282个窗口/玩家分数，最大误差为`5.55e-16`。排名、标准玩家ID、32个时间步的边界、有效回合边界以及行为者/武器/回合事件关联关系都会与生成的JSON进行比对。所有30个PNG文件均存在，具有正向维度且像素不恒定。一个实际的图表会被视觉检查；其轨迹、时间步轴、角度单位、射击标记和射击方向参考均清晰可读。所有选定的实际序列均使用射击方向的备用方案。在受控的端到端测试中已验证了观察到的受害者追踪，但在这些实际选定的候选中未展示出来。JSON和Markdown文件在本地保留，路径为`demo_analyzer/data/processed/m6_validation/`，被排除在Git之外作为生成输出。缺失演示的CLI案例也已执行，退出码为2，并明确报错。

<a id="temporary-directory-correction"></a>
### 临时目录修正

`.pytest_tmp*`文件夹源自本任务显式执行的`--basetemp=demo_analyzer/.pytest_tmp*`命令以及更早的手动测试运行。`pytest.ini`、`pyproject.toml`以及所有仓库脚本均未包含此类覆盖。测试用例使用原生`tmp_path`。所有后续测试命令均省略`--basetemp`，并使用pytest的原生临时存储（本主机上为`E:\Temp`）。沙箱中重映射的临时目录对pytest的清理操作不可访问；通过批准的执行访问解决了该环境问题，而无需修改测试用例或项目功能。在确认任务测试会话已完成并检查实际Python/pytest进程命令行后，仅在验证的仓库路径内删除了十个`.pytest_tmp*`目录。没有其他数据被删除。`.gitignore`还保护`.pytest_tmp*/`免受意外追踪；这只是一个防护措施，并非修复方案。完整的原生pytest执行完成后，进行目录检查：**仓库根目录或`demo_analyzer/`子目录下不存在任何`.pytest_tmp*`目录**。

<a id="initial-audit-limits"></a>
## 初始审计限制

软件流水线已实现并经过测试；M6**并未被完全声明为已验证**。M1至M5中不存在校准的行为概率和已验证的操作阈值，也未在此处被发明。本地RF/树路径贡献项可以重构预测结果，但无法确立因果重要性，也无法支持非树估计器家族。独立标签和已验证的CS2CD到演示的转移均不存在。模型元数据缺少提取/版本细节，因此结构兼容性无法确立科学有效性。实际目标追踪和完全关联的回合上下文如上所述仍部分展示。本次初始审计未重复完整数据集训练，也未进行留出模型对比，且未评估实时服务器。未提交任何代码或推送操作。

<a id="m6--targeted-robustness-validation-2026-10-14"></a>
# M6 — 目标鲁棒性验证（2026-10-14）

本后续验证了现有实现，保留了所有先前的本地编辑以及原始`m6_validation/`输出。生成的证据位于`demo_analyzer/data/processed/m6_robustness_20261014/`下：`reference/`，三个`before/`分析，三个`after/`分析，一个在`repeat/`中重复的`test.dem`分析，以及在`audit/<demo stem>/`中的独立检查。每个审计均包含`validation.json`、`raw_round_events.json`，以及每个未分配和穿越窗口的CSV/JSON清单。`corrections.diff`将此任务的变更隔离到三个实现文件中，这些文件来自原有的实现。

<a id="a-diagnosis"></a>
## A. 诊断

对于`test.dem`，确切的`partial`条件是42个未分配窗口和36个穿越边界窗口。所有十名玩家均已评分；所有2,272个符合条件的射门均生成完整的有限窗口。没有一个符合条件的射门或生成的特征行被遗漏。缺失的追踪和不可见的刺激并不决定此状态。

所有42个未分配的射门严格位于一个`round_end`之后和下一个`round_start`之前。该间隙通过解析的`round_officially_ended`事件独立确认，这些事件与下一个开始时间一致；原始解析输出中存在重复的官方结束事件。36个窗口包含完成回合的最终时间步后接结果时间步；6个窗口完全位于过渡期内。没有一个窗口包含两个不同的活跃回合。这36个穿越窗口是42个中的子集，而非额外集合。射门发生在前一个结束事件后的3至434个时间步内。没有缺失的开始/结束事件可以解释这42个情况。

这6个完全处于过渡期的窗口分别是LuchoG在射门时间步27003；Syzel在107079、107085和130735；以及squeezie在26993和27011。CSV清单记录了每位玩家的规范ID和源ID、名称、窗口边界、射门时间步、重建的秒数（`tick / 64`，而非实际时间戳）、前一个回合/结束、后一个回合/开始以及得分。完成回合的ID在`begin_new_match`之后按顺序规范化；原始事件`round`的值在开始和结束事件之间存在差异，并未被代入这些ID中。第一个保留的时间区间从最新的`begin_new_match`开始，时间步为5787，紧接在第一个实时开始时间步5786之后。

完成区间合同是包含性的`[start_tick, end_tick]`。根据此合同，一个结果后的射门没有活跃的完成回合关联。其前一个/后一个回合的上下文记录在诊断清单中；`round_number`保持为空，而非静默扩展合同。所有42个得分仍保留在其玩家的算术平均值中。

历史M3窗口包含32个连续的玩家时间步，以射门结束（31个时间间隔，0.484375秒，基于历史64Hz）。它们不按回合进行过滤。这36个结束穿越窗口遵循此定义并包含结果后的瞄准样本。它们在结束时的最大角度步进恰好为3.390503569度；最大位置步进为3.359422697个游戏单位。这些测量结果并未显示生成断点或损坏特征。若改变该群体，将改变M5输入定义并需要单独的兼容性/评估研究；此处并无此类变更或再训练的正当性。

两个缺陷影响实际输出：

* `weapon_fire` 使用诸如 `weapon_ak47` 的名称，而 `player_hurt`/`player_death` 使用 `ak47`。在所有评分窗口中，包括所有选定的轨迹，均排除了每项命中/击杀记录。在 M6 比较中仅移除可选前缀后，可恢复观察到的接触记录，而存储的武器或 M3/M5 特征保持不变。
* 将 Unicode 玩家名称打印到重定向的 Windows `cp1252` 标准输出中，会在报告写入后引发 `UnicodeEncodeError`。两个额外的真实演示最初因该原因退出状态为 1。不可编码的控制台字符现在使用反斜杠转义；JSON/Markdown 保留完整的 Unicode 标识。

合成回归测试也展示了当两个窗口端点均未知但一个完整回合位于其中时，遗漏的边界标志；缺失的后续 `round_start` 会重用前一个回合的开始，导致区间重叠；以及重复的结束事件会改变归一化的回合编号。边界检测现在检查实际的区间边界。解析器会去重结束时间点，并要求后续的开始时间严格位于前一个结束时间之后。这些解析器边缘情况不会改变三个真实演示的完成区间。

<a id="b-changes"></a>
## B. 变更

* `analysis.py`：可选武器前缀比较、边界检测、不可用追踪的明确原因以及 JSON/Markdown 中的回合数量限制。未对评分、特征、候选选择或窗口定义进行任何更改。
* `cli.py`：控制台玩家名称的安全编码。
* `parser/demo_parser.py`：如上所述的两行回合配对修正。
* `test_analysis.py` 和 `test_demo_parser.py`：新增 18 个合成案例。两个现有测试为报告和极端有限树输入新增了断言。
* README 和本内存：记录新证据的同时保留历史验证结果。
* `.gitignore`：排除本次验证生成的报告、图像、日志和参考快照。

现有的位置性 M5 聚合、带 ID 并列处理的排名、列选择、特征排序、有限值拒绝、树 float32 遍历以及描述性/科学性标签已正确运行。

<a id="c-tests-and-environment"></a>
## C. 测试与环境

基准：**274 个测试通过，耗时 22.07 秒**。六个回归案例在与保存的原始实现对比时失败：Unicode 标准输出、两种武器前缀方向、一个内部边界且端点未知、一个缺失的回合开始以及一个重复的结束事件。经过修正后，最终目标的 M1/M2/M6 运行通过 **76 个测试，耗时 20.68 秒**；完整的 M1–M6 套件通过 **292 个测试，耗时 22.59 秒**，无失败或跳过。目标运行包含所有 M6 的端到端集成测试。新增案例也涵盖了包含事件边界、无回合上下文的窗口以及缺失/单一/重复受害者遥测数据。现有的并列、输入顺序、身份、位置聚合、无效模型以及确定性测试套件保持不变。

第一个沙盒运行得到207个通过 / 67个测试用例错误，因为pytest无法使用重映射的临时目录。将进程本地的`TEMP`和`TMP`设置为原生系统目录`E:\Temp`，无需修改测试用例或pytest配置即可解决此问题。不会创建任何`.pytest_tmp*`目录。Python启动器在此执行环境中也会在stderr上打印`Failed to find real location of E:\Python\python.exe`，包括成功命令；但三个修正后的CLI退出码仍为0。未发现或隐藏任何解析异常。

所有36个可导入的包模块均成功导入。语法编译、`pip check`、已安装/模块CLI帮助、无效演示CLI退出码2以及`git diff --check`均通过。不存在配置的语法检查/类型检查命令。未发生依赖安装、模型训练、下载、提交或推送操作。

<a id="d-real-analyses"></a>
## D. 实际分析

在修正前后，均对本地可用的三个`.dem`文件进行了分析。未下载或修改任何文件。

|演示|识别/检测到的玩家|生成/评分的窗口|完成的回合|无回合|穿越|玩家得分最小/平均/最大|选定/PNG|追踪图表|CLI之后|执行前/后的秒数|
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| `test.dem` | 10 / 10 | 2272 / 2272 | 21 | 42 | 36 | 0.237090 / 0.251237 / 0.263435 | 30 / 30 | 4 | 0 | 143.85 / 37.75 |
| `2026-09-01_19-31-10_17_de_inferno_team_Kay_vs_team_YY.dem` | 10 / 11 | 3104 / 3104 | 23 | 129 | 42 | 0.235112 / 0.250149 / 0.259392 | 30 / 30 | 7 | 0 | 52.10 / 50.56 |
| `2026-09-02_19-03-20_18_de_ancient_team_alxska-_vs_team_Palmoleeve.dem` | 10 / 10 | 2800 / 2800 | 24 | 106 | 58 | 0.240015 / 0.249423 / 0.261043 | 30 / 30 | 9 | 0 | 60.58 / 40.06 |

每个状态保持为`partial`；JSON和Markdown均存在且一致。所有归一化的合格射门均具有评分窗口；无得分值为NaN或无穷大。Inferno保留了Steam ID为`76561198125674008`的标识，并具有遥测数据，但无合格射门且得分为空。Inferno的未分配窗口包括：38个位于已完成回合之间，4个位于最后一个完成回合之后但下一个回合开始之前，以及87个位于从tick 188682开始的最终回合中，且无结束事件。Ancient的106个未分配窗口位于已完成区间之间。每个真实的穿越都是一个回合边界；没有真实的窗口穿越到下一个回合的开始。时间记录包括不同并发验证工作，而非性能基准测试。

<a id="e-independent-beforeafter-checks"></a>
## E. 独立前后检查

所有8,176个窗口均从归一化的原始遥测和事件中重建。它们的六个特征值与保存的报告完全一致。持久化的RF再次预测这些原始输入：与报告窗口得分的最大差异为`2.78e-16`；独立计算的玩家平均值最大差异为`2.78e-17`。基线加上特征路径贡献能够将每个窗口/玩家得分恢复至`6.11e-16`以内。未出现超出`1e-12`的意外前后差异：身份、窗口边界、已完成区间、得分、排名、候选ID和贡献均保持一致。

对于`test.dem`，关联数量从2,272个射门仅变为2,272个射门加上320个命中和148个击杀关联。在所有窗口中，有347个窗口关联到有足够并发遥测的观察到的受害者；其中4个出现在每个玩家前三位选择中。其余1,925个窗口，包括26个选定序列，均未满足现有攻击者/武器/回合/两tick条件的接触。Inferno有515个可用追踪窗口（7个被选定）；Ancient有507个（9个被选定）。没有真实的关联目标缺乏足够的并发遥测，也没有在这些运行中因首次接触选择而被排除的后续可用受害者。合成的缺失/重复受害者情况保留了明确的射门方向后备。

传递给M2的数据会针对最终的90个图表中的每一个进行检查：演员、目标、样本时间步、边界、标题和角度几何结构。独立的float64几何结构与当前混合float32/float64计算结果的最大差异为`1.12e-6`度，没有任何M2公式被修改。所有图表均为1100×600的RGBA格式，数据非恒定，图像链接正确且数值有限。在三个演示中，对四个代表性图表进行了视觉检查，包括观察到的受害者和射击方向引用。只有预期的4/7/9跟踪PNG文件与基线存在差异。在没有观察到的可见性刺激的情况下，反应功能不可用。跟踪使用身体位置几何结构，不涉及可见性、眼高或命中框重建；在射击之后立即发生的命中可以合理地落在射击前的图表之外。

|`test.dem`玩家，等级未变|Windows|平均值前后对比（小数点后六位）|无循环/交叉|未分配/交叉窗口对玩家平均值的加性贡献|
|---|---:|---|---|---|
|1 MDMiro| 159 | 0.263435 / 0.263435 | 2 / 2 | 0.002642 / 0.002642 |
|2 KeaZy| 120 | 0.260880 / 0.260880 | 2 / 2 | 0.004495 / 0.004495 |
|3 LuchoG| 188 | 0.258100 / 0.258100 | 9 / 8 | 0.013038 / 0.011063 |
|4 YEL7OWORE| 375 | 0.256915 / 0.256915 | 2 / 2 | 0.001172 / 0.001172 |
|5 samu777-| 258 | 0.256882 / 0.256882 | 6 / 6 | 0.005533 / 0.005533 |
|6 NthraX| 250 | 0.252927 / 0.252927 | 11 / 11 | 0.012024 / 0.012024 |
|7 -s4ndor| 286 | 0.244495 / 0.244495 | 0 / 0 | 0 / 0 |
|8 squeezie| 225 | 0.244215 / 0.244215 | 4 / 2 | 0.004866 / 0.002441 |
|9 Syzel| 139 | 0.237428 / 0.237428 | 6 / 3 | 0.009635 / 0.004724 |
|10 Draw0x| 272 | 0.237090 / 0.237090 | 0 / 0 | 0 / 0 |

加性贡献是子集得分之和除以玩家总窗口数量，而不是子集平均值。重叠的子集不得合并相加。

`test.dem`的重复CLI安装运行耗时33.63秒。对每个报告字段的深度比较在绝对容差`1e-12`下未发现语义差异；所有30个PNG文件字节完全相同。JSON文件不完全相同：并行RF浮点求和（`n_jobs=-1`）最多会改变窗口得分`2.22e-16`。本次重复比较未遗漏任何报告字段，排名保持不变。不声明浮点得分的精确二进制可重现性。

所有三个源演示、模型元数据和模型字节的SHA-256哈希值在前后均一致。RF模型哈希值保持为`322ea64dddf12164824a5269371429ae87f714f7a2c0bf89c2eb10185cc09d11`。

<a id="f-manual-reproduction"></a>
## F. 手动重现

从仓库根目录开始，使用现有环境和本地系统临时目录：

```powershell
$env:TEMP = 'E:\Temp'
$env:TMP = 'E:\Temp'
.\.venv\Scripts\python.exe -m pytest -q demo_analyzer/tests/test_analysis.py demo_analyzer/tests/test_demo_parser.py demo_analyzer/tests/test_aim_visualization.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\cs2guard.exe analyze --help
.\.venv\Scripts\python.exe -m cs2guard_demo --help

$model = '.\demo_analyzer\models\supervised\random_forest_v1.joblib'
$modelHashBefore = (Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash
$runRoot = Join-Path '.\demo_analyzer\data\processed' ('m6_manual_' + [guid]::NewGuid().ToString('N'))
Get-ChildItem '.\demo_analyzer\data\raw\train_sources\demo' -Filter '*.dem' | ForEach-Object {
    $out = Join-Path $runRoot $_.BaseName
    .\.venv\Scripts\cs2guard.exe analyze $_.FullName --model $model --output $out
    if ($LASTEXITCODE -ne 0) { throw "Analysis failed: $($_.Name)" }
    $report = Get-Content -LiteralPath (Join-Path $out 'report.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $report.summary
    $report.players | Format-Table rank,player_id,score,window_count
    $report.review_events.visualization | Format-Table path,reference,sample_count
    if (-not (Test-Path -LiteralPath (Join-Path $out 'report.md'))) { throw 'Missing Markdown report' }
}
if ((Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash -ne $modelHashBefore) { throw 'Model changed' }
git diff --check
git status --short
Get-ChildItem -Force -Directory -Path '.', '.\demo_analyzer' -Filter '.pytest_tmp*'
```

记录于2026-10-14：76个目标/292个总测试，每个本地演示的CLI退出码为0，计数和得分如上所述，模型哈希值未变，且无`.pytest_tmp*`目录。重复分析将所有JSON字段与数值绝对容差`1e-12`进行比较；其他字段和所有PNG字节均匹配。

<a id="g-validation-status-and-limits"></a>
## G. 验证状态与限制

* 技术M6有效性：已验证现有推理合约并测试了错误情况。
* 数据与关联完整性：部分。已知的过渡和未完成的回合明确位于已完成回合覆盖范围之外。邻近接触属于时间上下文，而非因果射击归因。
* 多演示鲁棒性：已在所有三个可用本地演示上验证，未在任意录制格式或人群上验证。
* 科学评分在普通演示上的有效性：未验证。独立标签、领域迁移评估、适当的校准数据以及提取版本元数据均缺失。未引入新的操作阈值、作弊概率、裁决或再训练。移除`weapon_`不会推断出未记录的别名，例如伤害事件中被沉默武器的差异。

<a id="m6--presumed-legitimate-external-evaluation"></a>
# M6 — 假设合法的外部评估

`cs2guard_demo.validation`在`demo_analyzer/data/raw/held_out/legitimate/`下对本地演示进行评估，使用现有的冻结RF包。它直接调用M6，保留评分、特征、玩家身份、质量计数以及RF路径贡献。可选的`review_plots=False`参数会抑制本研究中每个玩家的瞄准PNG图像；普通M6调用保留其原有的图表。没有特征、窗口、评分、训练或校准协议的变更。

协议在外部推断**之前**被保存：模型/元数据的SHA-256值、精确源哈希值和源ZIP文件、Git状态、Python/依赖版本、32步/64Hz设置、有序特征、算术平均聚合、标签、自助法设置以及历史描述性阈值网格**0.10–0.90**。比较器为`>=`，如M5所示；**0.50不是操作阈值**。输出位于被忽略的`demo_analyzer/data/processed/validation_legitimate/`下，具有独立的内容寻址匹配尝试和研究目录。重复命令仅在接收到哈希值、身份、有限值、计数和玩家均值检查后才会重用报告。无效尝试和先前的研究仍可获取。

标签默认为`presumed_legitimate`，仅基于用户声明。可选的`--manifest` JSON文件将相对演示路径映射到来源和玩家覆盖。未知玩家保留在描述性输出中，并被排除在标志分母之外。一个确认的标签需要有个体覆盖并附有证据：

```json
{
  "match.dem": {
    "status": "presumed_legitimate",
    "evidence": "User-supplied recording; no independent adjudication",
    "players": {
      "demo:76561198000000000": {"status": "unknown"},
      "demo:76561198000000001": {
        "status": "confirmed_legitimate",
        "evidence": "Describe the individual verification here"
      }
    }
  }
}
```

主要单位是**玩家匹配**。描述性摘要保留缺失值、样本标准差和探索性尾部百分位。固定种子的95%分位数自助法区间对匹配进行重采样，保持匹配内部的依赖关系；第二次分析对共享持久ID的连接匹配进行重采样。当独立组件少于两个时，该区间不可用。威尔逊区间是明确的独立同分布敏感性参考，而非修正边界。零/全标志的自助法区间是退化的，无法建立总体FPR。该指标为`presumed_legitimate_flag_rate`，而非确认的FPR。

现有的`supervised_dataset.csv`提供了合法的CS2CD特征分布，包括单独报告的完整参考和精确的历史M5测试分割。持久化的模型评分在不拟合的情况下测试该参考。窗口特征/评分和等权重玩家匹配均值被分别报告。如果输入缺失，则不会重新生成或下载历史数据集。精确的原生演示重复项被排除；文件名/身份与三个历史M6报告的重叠被记录。CS2CD匿名化和不可用的独立会话标识符仍无法保证完全独立性。

从仓库根目录运行或继续整个研究，使用相同的命令：

```powershell
.\.venv\Scripts\python.exe -m cs2guard_demo.validation
```

阅读最新的研究并打开其报告/图表：

```powershell
$study = (Get-Content '.\demo_analyzer\data\processed\validation_legitimate\latest.json' -Raw -Encoding utf8 | ConvertFrom-Json).run_directory
$statistics = Get-Content (Join-Path $study 'statistics.json') -Raw -Encoding utf8 | ConvertFrom-Json
$statistics.counts
$statistics.eligible_player_match_scores
$statistics.flag_rates | Select-Object threshold,evaluable_player_matches,flagged_player_matches,presumed_legitimate_flag_rate
Invoke-Item (Join-Path $study 'report.md')
Get-ChildItem -LiteralPath $study -Filter '*.png' | Invoke-Item
.\.venv\Scripts\python.exe -m pytest -q
```

这项仅包含负样本的研究测量了分数分布和描述性标记率。它无法测量外部回忆、ROC-AUC或PR-AUC，无法验证校准性，无法识别作弊者，也无法证明泛化能力。

<a id="real-external-study--2026-10-14"></a>
## 真实外部研究 — 2026-10--14

所有 **九** 个可用的新演示版本均被分析：**90个评分/检测到的玩家匹配观察**，**57个可观察的Steam身份**，**29,010个评分窗口**，没有失败或排除的演示版本，也没有未评分的玩家。所有90个标签均基于用户声明被视为合法；没有任何标签被独立确认或标记为未知。所有报告均为`partial`：**685个窗口缺乏完整回合上下文**，且**415个窗口跨越回合边界**，根据历史提取合同予以保留。评分玩家的窗口数量范围为114至858（中位数为304.5）。

玩家匹配分数的平均值为 **0.249250**，中位数为 **0.244984**，样本标准差为 **0.014424**，最小值/最大值为 **0.225987/0.295459**，Q25/Q75为 **0.238631/0.255644**，P90/P95/P99为 **0.267843/0.279872/0.289260**。尾部百分位数仍处于探索阶段，仅有90个观测值。匹配分数范围为 **0.242817至0.256175**。十个身份在多个匹配中重复出现；其观察到的玩家内分数范围为 **0.001584至0.041159**，仅基于描述性证据。

在将九个匹配视为独立的情况下，平均分数的95%匹配自助区间为 **[0.246899, 0.251793]**。所有九个匹配通过重复玩家形成一个连通组件，其中包括一个在每个匹配中均出现的身份。因此，保持依赖关系的连通自助法没有可估计的区间。该狭窄的匹配自助区间不能被解释为可靠的总体精度。

在固定阈值 **0.10 和 0.20** 时，标记数量为 **90/90 个玩家匹配和 9/9 个匹配**。在 **0.30至0.90之间，包括0.50** 时，标记数量为 **0/90 和 0/9**。这些分母中没有标签或数据排除。零标记或全部标记的自助区间均为退化状态。在零标记情况下，独立同分布的威尔逊灵敏度参考区间为 **[0, 4.09%]**（基于90个观测值）和 **[0, 29.91%]**（基于9个匹配）；两者均未考虑实际共享玩家的依赖关系。零观测标记既不能确立零假阳性率，也不能确立作弊者灵敏度。

在九个文件之间或与三个历史M6演示版本之间均未出现完全相同的副本。**六个Steam身份与历史技术报告重叠**。这些记录属于新匹配，而非全新玩家群体；文件名/会话及CS2CD匿名化不确定性依然存在。M3发现仅限于`train_sources`；本次评估在其他方面进行，从未调用训练。现有M5输入仅包含 **397,487个CS2CD窗口**，且无可观察的外部匹配/玩家ID重叠；匿名化仍限制了真实个人的核查。

CS2CD比较使用了**282,022个合法窗口/1,801个玩家匹配**作为完整描述特征的参考基准，以及**66,588个合法窗口/402个玩家匹配**（覆盖64场历史测试对局）用于冻结RF分数的比较。窗口特征中位数的偏移量相对于参考IQR（大约为**−0.099至+0.010 IQR**）较小；等权重玩家匹配特征均值给出**−0.060至+0.040 IQR**。外部玩家评分更低且分布更分散：均值/中位数为**0.249250/0.244984**，而合法CS2CD测试观测值的均值/中位数为**0.284594/0.274929**。中位数相似并不意味着分布完全相同：窗口P99最大速度为**829.28对692.76度/秒**，P99速度标准差为**231.30对191.97度/秒**。这些是描述性分布差异，而非显著性检验、操作改进或作弊检测退化的证据。

最高玩家评分为**0.295459**，来自525个窗口，覆盖完整回合比例为**98.86%**（六个未分配窗口和五个跨窗口情况）。前五项观测值在报告中保留了特征极值和带符号的RF路径贡献；其中没有一项被判定为作弊行为。四个聚合PNG图表已进行人工视觉检查。

自动化基准测试：在修复无法访问的沙箱临时存储后，通过本地进程`TEMP`/`TMP`，共**292个测试通过**。在添加外部评估测试后，完整测试套件达到**330个通过**（新增38个案例）；语法编译和`pip check`测试均通过。测试覆盖了空输入/无效输入、重复项、清单文件、缺失/非有限值、速率/平局、聚类重采样、参考对比、报告保留、恢复功能、冻结模型完整性等场景。生成的产物包括JSON/CSV统计文件、Markdown报告、四张图表、冻结源码/协议证据以及每个对局的M6报告。模型与元数据均未更改；未提交任何代码或推送。实际恢复功能重新使用了全部九个已验证的对局报告，并精确重现了统计结果。对所有29,010个已保存特征行进行独立模型重新加载和推理，最大评分差异为**2.776e-16**；最大RF贡献重构误差为**6.661e-16**，两者均低于**1e-12**。该检查未独立重复源码解析过程。最终证据位于`demo_analyzer/data/processed/validation_legitimate/run-0ae2814792ffd726/verification.json`；`latest.json`指向研究报告和图表。

证据分类：技术处理已完成；验证标签仍保持假设状态；本样本中评分集中现象被观察到；阈值标志以描述性方式测量；分布差异可被观察到；外部作弊检测、校准与泛化能力仍**未验证**。

<a id="m6--cs2cd-evaluation-2026-10-15"></a>
# M6 — CS2CD评估（2026-10-15）

<a id="data-provenance-and-executed-protocol"></a>
## 数据、来源与执行协议

本地JSON/Parquet目录包含**795场CS2CD对局**。现有`supervised_dataset.csv`包含**397,487个保留窗口，来自317场对局**。重新应用历史分组划分（`test_size=0.20`，`random_state=42`）得到**253场训练对局 / 306,315个窗口 / 2,471个评分玩家匹配**，以及**64场测试对局 / 91,172个窗口 / 637个评分玩家匹配**。训练集包含1,399个合法和1,072个可疑玩家匹配；测试集包含**402个合法和235个可疑**玩家匹配，可疑比例为**36.8917%**。

原始测试标签包含 **640 个玩家-对战记录**。有三位合法阵容玩家没有任何保留特征且未得分：`126.json / Player_7`、`178.json / Player_8` 和 `217.json / Player_5` 没有原始 `weapon_fire` 事件。分类指标使用 637 个已评分的观测值；排名排除了这三位未得分的玩家，而 Hit@k 使用包含已评分标注嫌疑人的 64 个对战记录。标签与匹配范围内的标准 ID 在保留的历史 CSV 与原始 CS2CD 阵容之间保持一致。另外 **478 个 JSON/Parquet 对**，与历史分区均不重叠，不包含任何标注的作弊者。它们在检查的开发制品中不存在；这并不能证明它们从未被查看过。缺失的作弊者标注在现有适配器下变为 `legitimate`，且无法独立证实其合法性。

持久化的 **随机森林 v1** 在未进行拟合、调优或校准的情况下被使用。其 SHA-256 值为 `322ea64dddf12164824a5269371429ae87f714f7a2c0bf89c2eb10185cc09d11`。六个有序瞄准特征、预处理、**32 个连续玩家帧 / 64 Hz**、玩家对战得分的算术平均值以及按得分降序、ID 升序排序的对战记录顺序均保持不变。历史推断使用保留的标准化 CSV 特征；新增对战使用现有的 CS2CD 适配器和标准化构建器。**未评估任何原生 `.dem` 解析**。

适配器现在投影 **16 个消耗的 Parquet 列**，而非读取诊断对战中存在的全部 222 列。其归一化、特征提取和推断规则保持不变。在该真实对战中，完整读取和投影读取均产生 **完全相同的 1,622,913 个标准帧** 和 **5,443 个字节完全一致的特征行**（`io_projection_validation.json`）。这验证了单个对战的数据等价性；记录的单次运行时长并非基准。PyArrow，已为 Parquet 支持安装，现作为显式运行时依赖项。

历史包记录了计数和指标，但未记录数据指纹、分区列表或提取版本。当前划分是从当前 CSV 重建而来，其 SHA-256 值为 `05ab29065646747b997908e7a17fd181cf0a73328db4a372f8c7d3e171f8b437`。匹配的计数和冻结模型指标支持一致性；它们无法提供历史数据集身份的回顾性加密证明。

分类指标对已评分的玩家对战记录赋予相等权重。平均精度使用 `average_precision_score`，而非梯形 PR 面积。Hit@k 对包含已评分标注嫌疑人的对战记录赋予相等权重，并测量至少一个此类玩家是否在前 k 个位置内。固定的 **0.10–0.90** 阈值网格使用 `>=`；该阈值是描述性的，并未选择任何操作阈值。**5,000 次固定种子（42）百分位自助抽样对整个对战进行重采样**，保留了对战内部的依赖关系。置信区间基于冻结模型和独立对战；匿名化处理阻止了跨对战测量真实玩家间的重复依赖。窗口从未被视为独立的重采样观测值。

<a id="historical-test-reproduction"></a>
## 历史测试重现

|玩家-对战指标|结果|95% 对战自助置信区间|
|---|---:|---|
|ROC-AUC| 0.777898 | [0.729588, 0.819406] |
|平均精度| 0.683983 | [0.599999, 0.757946] |
|Hit@1| 44/64 = 0.687500 | [0.562500, 0.796875] |
|Hit@3| 59/64 = 0.921875 | [0.843750, 0.984375] |

所有64场历史测试对局均包含有标注的嫌疑对象。ROC-AUC和AP指标精确复现了元数据值 **0.7778977453159733 / 0.6839833414991215**，此前在M5中被四舍五入为 **0.7779 / 0.6840**。模型、人群、分组划分、聚合方式和指标定义均保持一致。这些对局已用于M5的评估和描述性阈值分析，因此这属于对历史实验的**复现**，而非对泛化能力的新独立估计。

|阈值|精确率|召回率|F1分数|假阳性率|真负数|假正数|假负数|真正数|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.3689 | 1.0000 | 0.5390 | 1.0000 | 0 | 402 | 0 | 235 |
| 0.20 | 0.3689 | 1.0000 | 0.5390 | 1.0000 | 0 | 402 | 0 | 235 |
| 0.30 | 0.6234 | 0.6340 | 0.6287 | 0.2239 | 312 | 90 | 86 | 149 |
| 0.40 | 0.8033 | 0.2085 | 0.3311 | 0.0299 | 390 | 12 | 186 | 49 |
| 0.50 | 1.0000 | 0.0851 | 0.1569 | 0.0000 | 402 | 0 | 215 | 20 |
| 0.60 | 1.0000 | 0.0340 | 0.0658 | 0.0000 | 402 | 0 | 227 | 8 |
| 0.70 | 1.0000 | 0.0170 | 0.0335 | 0.0000 | 402 | 0 | 231 | 4 |
| 0.80 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 402 | 0 | 235 | 0 |
| 0.90 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 402 | 0 | 235 | 0 |

该表格涉及的是玩家-对局的平均值；历史M5在对局层级的阈值指标具有不同的分母。在0.50阈值下，召回率仅为 **20/235**，尽管观察到的假阳性数量为零。其95%匹配抽样召回率区间为 **[0.046082, 0.126582]**；假阳性率区间为退化形式 **[0, 0]**，无法证明群体层面风险为零。当没有玩家被标记时，精确率按惯例为零。完整的阈值区间在`historical_test_metrics.json`中得以保留。

错误清单保留了十个低分标注嫌疑对象和十个高分的合法玩家。最低分的嫌疑对象是匹配`cs2cd_933b2a9d40151a48` / `Player_4`：**0.246399**，覆盖六个窗口，排名第十。另一个嫌疑对象在176个窗口中得分为**0.250059**，说明低分并不局限于窗口数量极少的玩家。最高分的合法玩家是匹配`cs2cd_966bc4025553eeec` / `Player_8`：**0.491801**，覆盖232个窗口，排名第一。一个标注的合法玩家在**20/64场对局中排名第一**；**5/64场对局**在前三名中没有标注的嫌疑对象。

合法玩家-对局得分的均值/中位数为 **0.284594 / 0.274929**，而标注嫌疑对象的均值/中位数为 **0.350395 / 0.318411**。历史对局的平均得分范围为 **0.262760–0.488359**，正例比例各异；其中39/64场对局使用了Dust II或Mirage地图。这些描述性差异并未揭示地图效应或因果解释。错误案例暴露了标注数据中遗漏的嫌疑对象和排名错误；它们并不构成对实际作弊的判定。

<a id="additional-cohort-with-negative-annotations"></a>
## 额外的负标注队列

已完成运行处理了全部 **478场额外对局**，并提取了 **1,268,375个窗口**。**477场对局 / 4,726个玩家-对局**获得了评分，所有评分均被标注为合法。名单中包含 **4,779个玩家-对局**，其中包括 **53个未评分玩家，分布在20场对局中**。完全未评分的对局`455.json`（`cs2cd_0835357838ac262a`）缺少`weapon_fire`事件，因此未生成任何特征窗口。未评分的名单条目保留了不可用的评分；未进行零值填充。分类的分母以及对局抽样均排除了不可用的评分；后者在477个评分对局中进行重采样。

在那20个JSON文件中检查`CS2CDAdapter.get_events()`，发现所有53个未评分玩家均**没有标准射击事件**：其中10个属于完全未评分的对局，其余43个属于其他19场对局。任何拥有标准射击事件的玩家均具备特征窗口。这描述的是所提供的标准数据，而非证明实际未发生射击行为（`data_quality_diagnostics.json`，`complete_cohort.unscored_player_shot_coverage`）。

现有的适配器保留了 **505,144,089 个原始tick行中的 498,335,087 个**，排除了 **6,809,002 个（1.3479%）**，这些数据缺失或非有限的必需身份、位置或视角值。这些总数来自完整的提取收据。对早期82个匹配样本中选出的两个匹配进行了单独诊断，复现了其被排除的计数，并发现位置和视角字段缺失。该选定诊断并未估计群体层面的原因，也未证明覆盖无偏。保留的规范窗口包含 **40,588,000 个tick行**；规范化的归一化和插值规则保持不变。

|阈值（>=）|真阴性（TN）|假阳性（FP）|假阳性率（FPR）|95% 匹配自助区间|
|---|---:|---:|---:|---|
| 0.10 | 0 | 4,726 | 1.000000 | [1.000000, 1.000000] |
| 0.20 | 1 | 4,725 | 0.999788 | [0.999361, 1.000000] |
| 0.30 | 3,483 | 1,243 | 0.263013 | [0.244794, 0.281640] |
| 0.40 | 4,526 | 200 | 0.042319 | [0.035001, 0.050266] |
| 0.50 | 4,665 | 61 | 0.012907 | [0.009072, 0.017143] |
| 0.60 | 4,702 | 24 | 0.005078 | [0.002736, 0.007877] |
| 0.70 | 4,708 | 18 | 0.003809 | [0.001693, 0.006356] |
| 0.80 | 4,712 | 14 | 0.002962 | [0.001264, 0.005078] |
| 0.90 | 4,714 | 12 | 0.002539 | [0.001055, 0.004435] |

在每一个阈值处，TP和FN均为零，且在提供的负样本标注下，精确率也均为零。**ROC-AUC、平均精度、召回率、F1分数和Hit@k均不可用**，这并非检测性能为零的证据：该群体中没有标注的正样本。FPR衡量的是与这些标注的分歧，而非被裁定的作弊行为。其区间依赖于评分覆盖率和独立匹配情况。该群体被单独保留，以保持历史测试集的患病率，并将其与M5进行比较。

**61 名玩家对局在 0.50 范围内覆盖了 44 个得分对局**，得分的均值/中位数为 **0.289650/0.273359**，P99 为 **0.518744**，最大值为 **0.997079**（`cs2cd_d63d08339edb4053 / Player_9`），基于五个窗口并排名第一。对局得分均值范围为 **0.248276 至 0.480783**。这些高分即使在历史测试误报率（FPR）为零的情况下，仍与标注不符；它们既未证实实际作弊，也未证明其不存在。标签、行为覆盖范围有限以及向本地演示的迁移仍是科学限制。

**12 名玩家对局得分至少为 0.90**，覆盖九个对局和 318 个窗口。重新检查确认了有限的特征和得分，包括最大值情况下的五个独立窗口；七个案例来自四个对局且无被丢弃的帧。这确立了异常值的存在，而非其原因；未应用额外的过滤或最小窗口阈值（`error_distribution_diagnostics.json`）。

<a id="executed-checks"></a>
## 执行了检查

评估退出状态为 **0**，`integrity.json` 被标记为 **完成**。所有训练/评估匹配交集均为空。模型、元数据和历史数据集的哈希值保持不变；历史ROC-AUC/AP差异恰好为零。重新加载冻结模型并重复推理，任何窗口得分的变化最多为 **5.551115123125783e-16**，低于 **1e-12** 的检查容差。独立重新计算的玩家均值与窗口得分均值一致。一次独立的原始源提取在单个匹配上重复了 **158 个窗口的字节级一致**；完整群体原始数据的重新提取未被声称。

一个独立的彻底验证器退出状态为 **0**，并从 **所有 478 个标准缓存 / 1,268,375 个窗口** 中重现了随机森林得分、玩家均值、排名、阵容覆盖率、指标和自助法区间，包括空缓存。它验证了所有 **478 个源Parquet哈希值**、**795 个JSON源**、冻结代码和源归档；归档对比确认了在Parquet读取变更下科学变换未发生改变。历史测试检查也通过了。这验证了持久化的标准特征和推理，而非完整的原始数据重新提取（`verification.json`，`verification_run.log`）。

完整性检查通过了 **407 个 SHA-256 指纹**，包括模型、元数据、历史数据集以及 **403 个历史 M6 输出文件**。三个历史输出目录中的文件集保持不变，包括 2026-10-14 年的鲁棒性及外部研究（`integrity_preservation.json`）。

完整的自动化测试套件通过了 **345 个测试**。`pip check`（语法编译）和 `git diff --check` 通过。**M6 状态：在功能和技术范围内已完成，并已进行内部科学评估记录**。这些软件检查并未建立校准概率、操作阈值、独立正例泛化能力或原生演示检测性能。

<a id="reproduction-and-retained-evidence"></a>
## 可重现性与保留证据

从仓库根目录开始：

```powershell
.\.venv\Scripts\python.exe demo_analyzer/scripts/evaluate_cs2cd.py
.\.venv\Scripts\python.exe -m pytest -q
```

输出被保留在被忽略的 `demo_analyzer/data/processed/validation_cs2cd_20261015/` 中。`protocol.json` 在推理前冻结了模型/元数据/数据集的哈希值、代码、版本、Git 状态和设置；`sources.zip` 保留了源文件。`partitions.json`、`raw_inventory.csv` 和 `raw_roster.csv` 识别匹配项和标签。历史窗口得分保留在 CSV 文件中；新群体窗口仍保留在每项匹配的规范特征缓存中，并使用冻结的推理路径。人口 CSV 文件保留了玩家的均值、排名、覆盖率和错误案例；`historical_test_metrics.json` 和 `unused_negative_metrics.json` 保留完整区间，`*_by_match.json` 保留匹配级别的结果。`extraction_integrity.json` 记录完整的原始/保留计数和源/特征哈希值；`integrity.json` 记录最终检查。`report.md` 对两个群体进行汇总。恢复检查缓存收据并重复评分和指标计算；另一个 `--output` 目录执行一次新的提取。中断尝试被单独归档，包括验证前的 Parquet 投影协议。先前的 M5/M6 艺术品以及 2026-10-14 年的外部研究被分别保留。

协议字段 `contract.raw_inventory_sha256` 通过 `digest_json(inventory)` 对库存的规范 JSON 表示进行哈希，而非对 `raw_inventory.csv` 的字节进行哈希；预期使用另一个 CSV 文件的哈希。

<a id="future-milestones"></a>
# 未来里程碑

M7 至 M10 仍为未来工作。上述 M6 验证限制依然可见，而非被转化为不支持的科学声明。
