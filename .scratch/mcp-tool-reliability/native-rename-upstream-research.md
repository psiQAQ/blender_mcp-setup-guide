# Windows 扩展暂存目录重命名：上游报告依据

核对日期：2026-10-11。这里只记录官方规范、官方源码与报告建议，没有向上游提交。

## 是否值得报告

建议准备一份聚焦“Windows 上短时子句柄占用导致原生扩展安装失败”的报告，附最小复现和有界重试实验。问题位于 Blender 自带的扩展安装器；当前官方源码仍在一次 `os.rename` 失败后立即返回失败。现有材料能够支持安装恢复能力的讨论，但是否按 bug 或 enhancement 接收，由 Blender 维护者判断。[当前固定版本源码](https://github.com/blender/blender/blob/754ebe3c4b4e1402a159df6e1e58823cc93ef887/scripts/addons_core/bl_pkg/cli/blender_ext.py#L4349-L4364)、[官方报告范围与非 bug 边界](https://developer.blender.org/docs/handbook/bug_reports/making_good_bug_reports/)

报告的新增价值是受控真实子句柄复现、短时占用与持续拒绝的区分，以及明确边界的恢复实验。Windows 重命名限制本身不能证明 Blender 实现错误；应让维护者评估安装器是否需要容忍可恢复的短时竞争。现有本地结果与限制见[修复说明](../../docs/native-install-fix.md)和[诊断记录](../../docs/native-install-diagnosis.md)。

## #130211 与当前源码

- 官方镜像提交 [`f03fba614d354c0a3a5d952798803715488679e6`](https://github.com/blender/blender/commit/f03fba614d354c0a3a5d952798803715488679e6) 的日期是 2024-11-28，标题为 `Fix #130211: Unhandled error installing extensions when renaming fails`。差异处理了目标名称被普通文件占用的情况，并捕获暂存目录重命名异常、输出错误、返回 `False`。该提交没有增加重试。
- 2026-10-11 通过官方 GitHub 镜像 API 读取的 `main` 为 [`754ebe3c4b4e1402a159df6e1e58823cc93ef887`](https://github.com/blender/blender/commit/754ebe3c4b4e1402a159df6e1e58823cc93ef887)，提交日期为 2026-10-10 22:39:30 UTC。该 commit 的 `scripts/addons_core/bl_pkg/cli/blender_ext.py` 第 4349–4364 行仍直接执行一次 `os.rename(filepath_local_pkg_temp, filepath_local_pkg)`，异常后输出 `ERROR` 并返回 `False`，没有本地补丁采用的 Windows 有界重试。相邻注释明确关联 #130211，并指出这一阶段失败可能使扩展处于未安装状态。[固定源码](https://github.com/blender/blender/blob/754ebe3c4b4e1402a159df6e1e58823cc93ef887/scripts/addons_core/bl_pkg/cli/blender_ext.py#L4349-L4364)
- [#130211 的完整讨论及当前状态](https://projects.blender.org/blender/blender/issues/130211)未成功读取；检索索引与相关提交只能证明其关联，不能证明当前没有其他重复报告、没有相关 PR，或已有 issue 应当重开。

建议按“新报告并关联 #130211”的方向准备文案，强调瞬时句柄竞争与可恢复性。提交前由用户在 tracker 同时搜索开放和关闭的报告；若 #130211 或其他报告已经覆盖相同触发条件并仍在跟进，就把这些证据补充到已有报告。不能把已核实的旧提交描述为“已解决所有 WinError 5”，也不能直接认定旧 issue 与新复现完全不同。[官方避免重复要求](https://developer.blender.org/docs/handbook/bug_reports/making_good_bug_reports/#avoid-duplicates)

## 报告准备要求

1. 目标是 Blender 项目的 [Issues](https://projects.blender.org/blender/blender/issues)。使用 Blender 的 `Help > Report a Bug` 可自动填入部分系统和版本信息；也可以在网页手填。报告应有公开可取得的复现步骤和附件，复杂日志、脚本宜作文件附件，正文只保留必要描述。[官方报告指南](https://developer.blender.org/docs/handbook/bug_reports/making_good_bug_reports/)
2. 提供 Windows 版本、Blender 完整版本、分支、构建 hash，以及 Broken / Worked 信息。没有验证过可正常工作的官方旧版时，应写 `Worked: unknown`，不能将本地修复版填写为官方正常版本。[Windows 系统信息](https://developer.blender.org/docs/handbook/bug_reports/making_good_bug_reports/windows_information/)、[报告质量要求](https://developer.blender.org/docs/handbook/bug_reports/help_triaging_bugs/)
3. 将最小 ZIP、受控真实句柄脚本和原版安装器的实际失败输出作为主复现；把随机发生的完整包安装和 ETW 作为补充证据。官方允许有清晰操作步骤、按一定概率触发的问题；报告不需要先证明所有 WinError 5 都有同一原因。[官方简化要求](https://developer.blender.org/docs/handbook/bug_reports/making_good_bug_reports/#simplify)
4. 尽量补测最新稳定版或近期 daily build，并明确是否使用 factory settings。官方分诊流程在无法复现时会要求近期版本和更清晰的步骤。当前 `main` 的源码阅读只证明实现仍存在，不能代替该版本的实际运行验证。[官方分诊流程](https://developer.blender.org/docs/handbook/bug_reports/triaging_playbook/)

## 本次核对状态

| 项目 | 状态 | 边界 |
| --- | --- | --- |
| #130211 关联提交及补丁 | Passed | 官方 GitHub 镜像提交内容已读取 |
| 固定 `main` commit 的安装提交步骤 | Passed | 静态源码确认仍为单次 rename；文件 blob SHA 为 `8c1b3cc89852e7f6b8b4bc8922a9f78da1e1e206` |
| 官方报告要求 | Passed | 使用官方开发文档的检索内容；页面直接读取返回访问错误 |
| #130211 全文、当前 issue / PR 去重 | Not Run | tracker 访问受限，不能宣称不存在重复项 |
| 当前 `main` / daily build 实际复现 | Not Run | 本次没有运行 Blender 或下载构建 |
| 外部提交 | Not Run | 文案由用户自行提交 |
