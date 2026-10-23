[English](cs2cd.md) | [Français](cs2cd.fr.md) | [简体中文](cs2cd.zh-CN.md)

[项目 README](../../README.zh-CN.md)

<a id="cs2cd-integration"></a>
# CS2CD 集成

<a id="purpose"></a>
## 目的

本文件描述了如何将 CS2CD 数据集集成到 CS2Guard 数据集构建器中。

CS2CD 被用作一个外部的、带有标签的《反恐精英 2》对战数据源。其特定来源的表示形式会在被用于特征提取和机器学习流程之前，转换为标准的 CS2Guard 数据集格式。

<a id="source-data"></a>
## 源数据

一个 CS2CD 对局由两个互补文件表示：

- JSON：对局元数据、游戏事件和作弊者标注
- Parquet：逐帧玩家遥测数据

集成流程为：

CS2CD JSON + Parquet → CS2CD 适配器 → 标准 CS2Guard 数据 → 特征提取 → 数据集流程

<a id="cs2cd-adapter"></a>
## CS2CD 适配器

CS2Guard 使用位于以下位置的专用适配器：

`src/cs2guard_demo/dataset/adapters/cs2cd.py`

适配器目前处理：

- 对局元数据
- 逐帧玩家数据
- 射击事件
- 命中事件
- 击杀事件
- 合法/可疑标签

将此逻辑保留在适配器内部，可以防止 CS2Guard 的其余部分直接依赖 CS2CD 格式。

<a id="player-labels"></a>
## 玩家标签

CS2CD 提供了明确的标注，用于识别作弊玩家。

这些标注被转换为 CS2Guard 标签：

- 被列为作弊者的玩家 → `suspicious`
- 对局中其他玩家 → `legitimate`

因此，标签来源于外部数据集，而不是从 CS2Guard 的行为特征中推断得出。

<a id="anonymous-player-identities"></a>
## 匿名玩家身份

CS2CD 使用诸如 `Player_1`、`Player_2` 或 `Player_3` 这样的标识符对玩家进行匿名化。

这些标识符仅在对局范围内有效，不应被视为全局唯一的玩家身份。

例如：

`Match A / Player_3`

和：

`Match B / Player_3`

可能对应两个完全不同的真实玩家。

因此，一个玩家在一个对局中可能是可疑的，而另一个使用相同匿名标识符的玩家在另一个对局中可能是合法的。

CS2Guard 将 CS2CD 玩家身份限制在其对局范围内。

例如：

`source_player_id = Player_3`

在概念上变为：

`player_id = cs2cd:<match_id>:Player_3`

这防止了不同对局中的匿名玩家被错误合并。

<a id="data-leakage-limitation"></a>
## 数据泄露限制

原生 CS2 对战录像可以提供持久的 Steam ID，使 CS2Guard 能够在多个对局中识别同一玩家。

CS2CD 通过匿名化移除了这一信息。

因此，CS2Guard 可以保证同一个 CS2CD 对局不会出现在训练、验证或测试划分中。

然而，CS2Guard 无法保证同一个真实玩家不会在不同的 CS2CD 对局中以匿名形式出现。

在评估使用 CS2CD 训练或测试的模型时，必须考虑这一限制。

<a id="current-status"></a>
## 当前状态

CS2CD 适配器已实现，并通过自动化测试覆盖。

适配器目前能够标准化元数据、事件、帧级数据和玩家标签。

适配器已集成到标准数据集构建器以及M4/M5实验中，记录在演示分析器项目内存中。自动化测试使用受控的JSON/Parquet测试数据集，并覆盖非有限遥测数据和每个比赛范围内的匿名身份。M6审计不会重复历史全数据集训练实验。

多源构建器会写入稳定的事件/周期CSV表头。若历史输出具有不同的表头，则无法安全地恢复。在未使用`--resume`的情况下，需保留所有研究成果；构建器在重新构建时会替换其生成的CSV文件。
