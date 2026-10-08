# Issue tracker: Local Markdown

本仓库的任务与规格保存在 `.scratch/` 中。

## 文件约定

- 每个功能使用一个目录：`.scratch/<feature-slug>/`。
- 规格文件为 `.scratch/<feature-slug>/spec.md`。
- 实施任务逐项保存为 `.scratch/<feature-slug>/issues/<NN>-<slug>.md`，从 `01` 开始编号。
- 分诊任务在文件顶部使用 `Status:` 行记录状态，名称见 `triage-labels.md`；使用 `Category: bug` 或 `Category: enhancement` 记录类别。
- 评论与讨论追加在文件末尾的 `## Comments` 下。

## 发布与读取任务

技能要求“发布到 issue tracker”时，在对应功能目录创建文件。
技能要求“读取相关 ticket”时，读取用户引用的路径；仅提供编号时，在对应功能目录内定位文件。

## Wayfinding

供 `/wayfinder` 使用：

- 工作地图：`.scratch/<effort>/map.md`，包含 Notes、Decisions-so-far 和 Fog。
- 子任务：`.scratch/<effort>/issues/<NN>-<slug>.md`，从 `01` 开始编号，正文记录问题。
- `Type:` 记录 `research`、`prototype`、`grilling` 或 `task`。
- Wayfinding 的 `Status:` 使用 `open`、`claimed`、`resolved`，适用于探索子任务的领取和解答流程。
- 依赖在顶部记录为 `Blocked by: NN, NN`；所有依赖均为 `resolved` 时解除阻塞。
- 扫描子任务目录，按编号选择第一个处于 `open` 且依赖已解决的任务。
- 开始工作前，先将状态改为 `claimed` 并保存。
- 完成后在 `## Answer` 下追加答案，将状态改为 `resolved`，并向地图的 Decisions-so-far 追加摘要和文件链接。
