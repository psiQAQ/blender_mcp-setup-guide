# Repository instructions

## Build cache

本地只保留 `build/latest/` 中最新一套完整成果与当前锁定输入；运行环境放在 `build/.working/`，结束后清理。修改构建、测试、网站入口或整理缓存前，读取 `docs/agents/build-cache.md`。失败保留最新诊断，并准确标记旧成果的来源和状态。

## Agent skills

### Issue tracker

任务与规格使用本地 Markdown；读取、创建或更新任务前，先读 `docs/agents/issue-tracker.md`。

### Triage labels

使用默认五种 triage 状态；分诊或更新任务状态前，先读 `docs/agents/triage-labels.md`。

### Domain docs

领域文档采用 single-context；探索代码、讨论术语或架构决策前，先读 `docs/agents/domain.md`。
