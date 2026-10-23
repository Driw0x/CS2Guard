[English](README.md) | [Français](README.fr.md) | [简体中文](README.zh-CN.md)

<a id="cs2guard"></a>
# CS2Guard

**基于机器学习的行为作弊检测系统——用于《反恐精英2》**

CS2Guard 是一个实验性的机器学习项目，旨在检测《反恐精英2》中的可疑玩家行为。

该项目首先从 **对 CS2 演示文件的离线分析** 开始，提取游戏数据，构建行为特征，建立数据集，并训练检测模型。

长期目标是将该项目演进为一个 **实时服务器端反作弊系统**，能够在比赛过程中持续分析玩家行为，而无需依赖侵入性的客户端监控。

> **状态：** 🚧 开发中 **开发方式：** 🤖 人工智能辅助

<a id="quick-start"></a>
## 快速入门

从仓库根目录开始，使用 Python 3.11 或更高版本安装，并运行测试（PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
```

要分析一个演示文件，请提供一个 `.dem` 文件和一个可信的 M5 `.joblib` 模型及其相邻的 `.json` 元数据。请根据你的文件路径调整输入路径：

```powershell
.\.venv\Scripts\cs2guard.exe analyze '.\demo_analyzer\data\raw\train_sources\demo\test.dem' --model '.\demo_analyzer\models\supervised\random_forest_v1.joblib' --output '.\demo_analyzer\data\processed\manual_analysis'
```

打开 `demo_analyzer/data/processed/manual_analysis/report.md` 以查看排名和 PNG 链接；`report.json` 包含所有评分窗口。若没有 `--output`，报告将保存到工作目录中的 `<demo stem>_analysis/`。

一个全新的克隆版本包含模型元数据，但不包含训练好的模型或演示文件：`.joblib` 和 `.dem` 文件被 Git 忽略。安装和测试无需这些文件。推理需要两者，且不会训练模型；有关单独的训练流程和数据集要求，请参阅 [模型前提条件](docs/demo_analyzer_memory.zh-CN.md#reproducible-validation)。

<a id="contents"></a>
## 内容

* [项目目标](#-project-goals)
* [项目方法](#-project-approach)
* [快速入门](#quick-start)
* [路线图](#️-roadmap)
* [项目架构](#️-project-architecture)
* [技术栈](#️-tech-stack)
* [检测策略](#-detection-strategy)
* [研究挑战](#️-research-challenges)
* [文档 / 技术记忆](#documentation--technical-memory)

---

<a id="-ai-assisted-development"></a>
## 🤖 人工智能辅助开发

AI 工具将辅助代码编写、测试、文档和研究工作。架构设计、实验和集成仍需人工审查与验证。

---

<a id="-project-goals"></a>
## 🎯 项目目标

探究是否可以通过服务器可观测的游戏行为揭示可疑行为，而无需侵入性的客户端监控：

* 瞄准移动轨迹、十字准星位置和目标追踪行为
* 反应时间、角速度和加速度
* 射击行为、玩家移动、敌我感知以及开火前的模式

开发初期从离线演示文件研究和模型训练开始，随后目标是实现实时服务器端检测。

---

<a id="-project-approach"></a>
## 🧠 项目方法

<a id="stage-1--offline-demo-analysis"></a>
### 阶段 1 — 离线演示分析

离线分析器解析已录制的比赛，提取行为特征，并在无实时约束条件下评估机器学习模型。

```text
CS2 Demo
    │
    ▼
Demo Parser
    │
    ▼
Normalized Game Data
    │
    ▼
Feature Extraction
    │
    ▼
ML Detection
    │
    ▼
Suspicion Score
```

<a id="stage-2--real-time-server-side-detection"></a>
### 阶段 2 — 实时服务器端检测

计划中的服务器端系统将把离线流程适配到实时遥测数据中，尽可能复用已有的特征和模型。

```text
CS2 Server
    │
    ▼
Live Game Events
    │
    ▼
Event Buffer
    │
    ▼
Feature Extraction
    │
    ▼
ML Inference
    │
    ▼
Risk Aggregation
    │
    ▼
Player Suspicion Score
```

<a id="documentation--technical-memory"></a>
## 文档 / 技术记忆

* [演示分析项目记忆](docs/demo_analyzer_memory.zh-CN.md)：实现细节、实验过程、评估指标和验证协议。
* [服务器端项目内存](docs/server_anticheat_memory.zh-CN.md)：未来实时架构与研究。

---

<a id="️-roadmap"></a>
# 🗺️ 进展路线图

<a id="m1--demo-parsing"></a>
## M1 — 解析演示功能

构建从CS2演示文件中提取结构化游戏数据的基础。

* [x] 配置Python项目结构
* [x] 集成CS2演示解析器
* [x] 加载并解析`.dem`文件
* [x] 提取比赛元数据
* [x] 提取玩家和队伍信息
* [x] 提取回合信息
* [x] 提取每帧玩家位置
* [x] 提取视角角度（俯仰角/偏航角）
* [x] 提取武器信息
* [x] 提取射击、命中和击杀事件
* [x] 定义标准化的`Match`、`Player`、`Round`、`Tick`和`Event`结构
* [x] 为演示解析添加测试用例

---

<a id="m2--aim-feature-engineering"></a>
## M2 — 射击行为特征工程

将原始游戏数据转化为可量化的瞄准行为指标。

* [x] 计算十字准星方向
* [x] 计算十字准星到目标的角距离
* [x] 计算角速度
* [x] 计算角加速度
* [x] 检测目标获取行为
* [x] 测量反应时间
* [x] 测量跟踪误差
* [x] 测量瞄准修正与超调
* [x] 检测潜在的瞄准瞬间
* [x] 将射击事件与瞄准序列关联
* [x] 可视化瞄准轨迹
* [x] 在选定的演示序列上验证特征

---

<a id="m3--dataset-builder"></a>
## M3 — 数据集构建器

创建一个可复现的流程，用于从多个比赛生成适用于机器学习的数据集。

* [x] 自动处理多个演示文件
* [x] 生成事件级样本
* [x] 生成玩家级样本
* [x] 生成时间窗口样本
* [x] 存储提取的特征
* [x] 处理缺失或无效数据
* [x] 归一化数值特征
* [x] 增加合法/可疑标签的支持
* [x] 创建训练/验证/测试划分
* [x] 防止比赛和玩家之间的数据泄露
* [x] 生成数据集统计信息
* [x] 定义CS2Guard数据集的标准结构
* [x] 支持并标准化外部数据集（如CS2CD）至标准结构

M5评估中强制执行比赛级隔离。玩家隔离依赖于可用身份；CS2CD的匿名化处理无法保证不同比赛间的真实玩家不重叠。

<a id="external-datasets"></a>
### 外部数据集

**CS2CD**适配器将匿名化的游戏行为和玩家级作弊标签映射至标准结构。详情请参见[集成细节与限制](docs/datasets/cs2cd.zh-CN.md)。

---

<a id="m4--anomaly-detection"></a>
## M4 — 异常检测

构建首个无需大量标注作弊数据的基于机器学习的行为检测器。

* [x] 建立合法行为的统计基准线
* [x] 实现孤立森林算法
* [x] 探索局部异常因子方法
* [x] 对单类SVM进行实验
* [x] 比较异常检测方法
* [x] 为单个事件生成异常分数
* [x] 为玩家生成异常分数
* [x] 分析误报
* [x] 识别最具影响力的特征
* [x] 定义初始怀疑评分策略

---

<a id="m5--supervised-detection"></a>
## M5 — 监督检测

当足够可靠的标注数据可用时，训练分类模型一次。

* [x] 构建标注数据集
* [x] 建立基线分类器
* [x] 训练随机森林模型
* [x] 尝试梯度提升模型
* [x] 调优模型超参数
* [x] 测量精确率
* [x] 测量召回率
* [x] 测量F1分数
* [x] 测量ROC-AUC / PR-AUC
* [x] 分析误报率
* [x] 比较监督检测与异常检测方法
* [x] 增加模型版本控制和持久化

在历史CS2CD保留的对局中，随机森林实现了玩家对局的**ROC-AUC 0.7779 / PR-AUC 0.6840**，而LOF为**0.6323 / 0.4624**。详见[M5结果](docs/demo_analyzer_memory.zh-CN.md#result-4)中的指标和阈值权衡。

---

<a id="m6--demo-analyzer"></a>
## M6 — 演示分析器

* [x] 通过单条命令分析整个演示文件
* [x] 分析比赛中的每位玩家，保留未获得足够数据的玩家且不生成分数
* [x] 使用M5窗口平均值为每位玩家生成整体怀疑分数
* [x] 生成带有单位和可用性的独立行为描述指标
* [x] 按怀疑分数对玩家进行排序，并确定并列情况的确定性排序
* [x] 识别需要检查的回合，保留未知回合关联
* [x] 识别需要检查的事件，而不声明已验证的作弊阈值
* [x] 解释测量特征、全局重要性以及带符号的局部RF/树概率贡献
* [x] 可视化用于检查的瞄准序列
* [x] 生成JSON和Markdown格式的比赛分析报告
* [x] 为演示分析构建命令行界面

<a id="m6-usage-and-validation"></a>
### M6的使用与验证

使用[快速入门](#quick-start)中的命令，配合训练好的M5包。报告包含玩家排名、审查序列、JSON/Markdown格式以及瞄准图。

**验证：** M6为三个技术演示录制和九个被认定为合法的外部演示生成了报告。在**64个历史CS2CD测试对局**上使用冻结的随机森林推理，重现了M5玩家对局的**ROC-AUC 0.7779 / 平均精确率 0.6840**，其中**Hit@1 44/64**，**Hit@3 59/64**。这些对局在M5阶段已进行评估；本次是重现，而非独立验证。

另外，**478个仅含负标注的CS2CD对局**产生了**4,726个评分的玩家对局**（来自477个对局）。在描述性阈值0.50下，**61/4,726被标记（描述性标记率1.29%；95%匹配自助区间0.91–1.71%）**，这些标注来自这些对局。该群体无法衡量判别能力或召回率；其未出现在检查的开发制品中，并不证明它从未被查看过。

评分是未经校准的模型输出。0.50阈值没有实际验证；标注的误报率无法估算生产环境下的假阳性率。CS2CD JSON/Parquet评估并未验证原生演示解析或独立确认的新作弊者检测能力。

请参阅[CS2CD结果和协议](docs/demo_analyzer_memory.zh-CN.md#m6--cs2cd-evaluation-2026-10-15)和[演示分析器实现](docs/demo_analyzer_memory.zh-CN.md#m6--demo-analyzer)，以获取详细证据和局限性。

---

<a id="m7--temporal-modeling"></a>
## M7 — 时间建模

调查基于序列的机器学习模型是否能提升行为检测能力。

模型将分析连续的帧数据：

```text
Tick t
Tick t+1
Tick t+2
...
Tick t+n
    │
    ▼
Temporal Model
```

* [ ] 定义固定长度的帧序列
* [ ] 构建一个时间序列数据集
* [ ] 实现一个简单的时序基线模型
* [ ] 尝试使用1D卷积神经网络模型
* [ ] 尝试使用LSTM / GRU模型
* [ ] 尝试使用基于Transformer的模型
* [ ] 比较时序模型与特征模型的表现
* [ ] 测量推理性能
* [ ] 分析哪些序列会触发预测
* [ ] 将最优模型集成到演示分析器中

**里程碑成果：** CS2Guard能够将玩家行为视为时间序列而非仅依赖聚合统计信息。

---

<a id="m8--awareness-analysis"></a>
## M8 — 意识分析

超越瞄准行为，扩展对可疑敌方意识的检测分析。

* [ ] 确定每个相关帧中敌方的可见性
* [ ] 计算十字准星与敌方的对齐情况
* [ ] 检测对不可见敌方的十字准星跟踪行为
* [ ] 分析瞄准前的行为
* [ ] 分析开火前的时机
* [ ] 考虑最近可见的敌方单位
* [ ] 在可能的情况下考虑队友信息
* [ ] 在可能的情况下考虑声音相关的信息
* [ ] 构建与意识相关的特征
* [ ] 定义一个意识异常评分
* [ ] 评估对合法玩家的误报情况
* [ ] 将意识信号融入全局可疑评分

在情境中解读意识：声音、队友、常见视角和游戏直觉可以解释看似预判的行为。

**里程碑成果：** CS2Guard在评估可疑行为时，结合了瞄准相关和敌方意识信号。

---

<a id="m9--real-time-detection-engine"></a>
## M9 — 实时检测引擎

将离线机器学习流程适配到实时游戏数据流中。

```text
Live Events
    │
    ▼
Sliding Window
    │
    ▼
Feature Engine
    │
    ▼
ML Model
    │
    ▼
Risk Aggregator
    │
    ▼
Suspicion Score
```

* [ ] 定义演示数据和实时数据的通用表示格式
* [ ] 实现实时事件缓冲区
* [ ] 实现滑动时间窗口
* [ ] 将离线特征转换为增量特征
* [ ] 持续运行机器学习推理
* [ ] 在事件间保持玩家状态
* [ ] 随时间聚合预测结果
* [ ] 持续更新玩家可疑评分
* [ ] 测量特征计算延迟
* [ ] 测量模型推理延迟
* [ ] 处理不完整的实时信息
* [ ] 比较离线与在线模型的性能

**里程碑成果：** 检测流水线可以对实时流进行增量处理，而不再需要完整演示文件。

---

<a id="m10--server-side-real-time-anti-cheat"></a>
## M10 — 服务器端实时反作弊

将检测引擎集成到CS2的服务器端环境中。

```text
             ┌─────────────────┐
             │   CS2 Server    │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Game Telemetry  │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Feature Engine  │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │  ML Inference   │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Risk Aggregator │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Suspicion Score │
             └─────────────────┘
```

* [ ] 调研可用的CS2服务器端遥测数据
* [ ] 构建服务器数据接入层
* [ ] 将服务器事件转换为CS2Guard的标准化格式
* [ ] 将实时遥测数据连接到流式功能引擎
* [ ] 在对局期间运行机器学习推理
* [ ] 为每位玩家维持实时怀疑分数
* [ ] 实现可配置的检测阈值
* [ ] 生成服务器端警报
* [ ] 记录可疑事件以供后续审查
* [ ] 存储证据用于离线分析
* [ ] 测量端到端检测延迟
* [ ] 测量对服务器性能的影响
* [ ] 与多个同时在线玩家进行测试
* [ ] 将实时结果与赛后演示分析器结果进行对比
* [ ] 构建管理员监控界面
* [ ] 在受控对局中评估完整系统

**里程碑成果：** CS2Guard作为一项实验性的实时、服务器端机器学习行为反作弊系统，适用于《反恐精英2》。

---

<a id="️-project-architecture"></a>
# 🏗️ 项目架构

```text
CS2Guard/
│
├── data/
│
├── demo_analyzer/
│   ├── data/
│   ├── models/
│   │   └── supervised/
│   ├── scripts/
│   ├── src/
│   │   └── cs2guard_demo/
│   │       ├── dataset/
│   │       │   └── adapters/
│   │       ├── detection/
│   │       ├── features/
│   │       ├── models/
│   │       ├── parser/
│   │       ├── supervised/
│   │       ├── utils/
│   │       └── visualization/
│   └── tests/
```

演示文件及未来服务器适配器旨在实现共享的游戏状态表示与分析流水线：

```text
Demo Parser ─────┐
                 │
                 ▼
              Game State
                 │
                 ▼
            Feature Engine
                 │
                 ▼
             ML Detector
                 │
                 ▼
           Suspicion Score
                 ▲
                 │
Server Stream ───┘
```

---

<a id="️-tech-stack"></a>
# 🛠️ 技术栈

<a id="currently-used"></a>
## 当前使用

<a id="core"></a>
### 核心组件

* Python
* NumPy
* pandas
* demoparser2

<a id="machine-learning"></a>
### 机器学习

* scikit-learn
* joblib（模型持久化）

梯度提升使用scikit-learn的`HistGradientBoostingClassifier`。

<a id="data-analysis--visualization"></a>
### 数据分析与可视化

* Matplotlib
* pytest（开发测试）

<a id="planned--under-investigation"></a>
## 规划中 / 正在调查

* PyTorch和时序模型（M7）
* 实时遥测数据接入与流式推理（M9–M10）
* XGBoost / LightGBM和Jupyter仍属于原始技术栈的候选方案；它们并非集成依赖项。

---

<a id="-detection-strategy"></a>
# 📊 检测策略

M6对每位玩家在M5窗口内的得分进行平均。长期策略是结合多个行为信号随时间变化：

```text
Raw Gameplay
     │
     ▼
Behavioral Features
     │
     ▼
Event Anomaly Scores
     │
     ▼
Temporal Aggregation
     │
     ▼
Behavioral Scores
     │
     ▼
Global Suspicion Score
```

额外行为得分及其组合仍属于未来研究内容。

---

<a id="️-research-challenges"></a>
# ⚠️ 研究挑战

* **误报与技能水平：** 某些不寻常机制可能是合法的；需在不同技能水平之间进行玩家对比，并在时间维度上聚合证据。
* **数据集质量：** 获取可靠标签和独立评估群体非常困难。
* **游戏情境：** 声音、队友信息、过往视野以及预期时间点可以解释看似可疑的行为。
* **离线到在线：** 实时推理必须在低延迟和有限服务器开销的前提下，处理不完整信息、玩家状态以及并发玩家的情况。

```text
Anomaly ≠ Cheater
```

---

<a id="-research-questions"></a>
# 🔬 研究问题

1. 哪些目标和意识特征能够将可疑行为与技能表现及合法情境区分开来？
2. 异常检测、监督学习和时序模型在性能上如何比较，哪些特征能够解释它们的预测结果？
3. 如何在控制误报的前提下，将多个弱信号进行融合？
4. 在迁移到实时遥测数据后，准确率能保留多少，推理过程能否满足服务器延迟要求？

---

<a id="-long-term-goal"></a>
# 🚀 长期目标

研究游戏遥测数据是否能够支持一种实验性的实时、服务器端反作弊系统，并逐步推进至M1至M10阶段。

---

<a id="-disclaimer"></a>
# 📌 声明

CS2Guard是一个实验性的研究与教育项目。

异常评分或可疑评分较高**并不**意味着玩家确实在作弊。合法玩家也可能表现出异常行为，任何实际的反作弊系统都必须考虑不确定性与误报问题。

CS2Guard与Valve Corporation无任何关联或官方背书。
