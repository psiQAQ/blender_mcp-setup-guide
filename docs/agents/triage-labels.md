# Triage labels

本地分诊任务使用以下映射，在 `Status:` 行记录状态。

| 技能中的角色 | 本仓库的状态 | 含义 |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | 等待维护者评估 |
| `needs-info` | `needs-info` | 等待报告者补充信息 |
| `ready-for-agent` | `ready-for-agent` | 规格充分，可由 agent 实施 |
| `ready-for-human` | `ready-for-human` | 需要人工实施 |
| `wontfix` | `wontfix` | 不实施 |

技能引用某个 triage 角色时，使用表中的本仓库状态。
每个分诊任务保留一个 triage 状态；类别按 issue tracker 文件中的 `Category:` 约定记录。
