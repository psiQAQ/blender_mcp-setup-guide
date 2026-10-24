# Issue title

Windows: extension installation fails on a short-lived child file handle

# Issue body

````markdown
### System Information

- Operating system: Windows 11 Pro 23H2, build 22631.4751, x64.
- Graphics card: NVIDIA GeForce RTX 4070 Ti SUPER.
- Graphics driver: NVIDIA 572.83.
- Relevant conditions: the original intermittent failure occurred while installing into a disposable extension repository inside a development workspace. The standalone reproduction uses only the bundled Python and Windows filesystem APIs; it does not require a graphics context, a particular monitor setup, user preferences, a third-party add-on, an editor, or administrator permissions.

The system and GPU information above was checked on 2026-10-11.

### Blender Version

**Broken:** the following official installers were tested:

| Blender | Build hash | Branch | Bundled Python |
| --- | --- | --- | --- |
| 5.1.1 | `b70da489d7f4` | `blender-v5.1-release` | 3.13.9 |
| 5.2.2 LTS | `d13f752e3b9c` | `blender-v5.2-release` | 3.13.13 |

**Worked:** unknown; no older working official version has been identified. This is not claimed to be a regression from a particular release. A locally modified installer is used only as a recovery experiment, not as a known-good official version.

The original-file tests use byte-verified backups retained before applying a local patch. Original `blender_ext.py` SHA-256:

- 5.1.1: `3738e7660bdaa7493d756be3132274eef6eb748305a16cf957f5e324573e93da`
- 5.2.2: `246cb49882f6129340767023bdc28e98c8ea6e743f64ebbff8aec774f842e5e1`

Current main was inspected at [`754ebe3c4b4e1402a159df6e1e58823cc93ef887`](https://github.com/blender/blender/blob/754ebe3c4b4e1402a159df6e1e58823cc93ef887/scripts/addons_core/bl_pkg/cli/blender_ext.py#L4349-L4364): the corresponding operation still attempts `os.rename` once and returns failure on an exception. A daily build from this commit has **not** been run.

### Description of the Issue

**Actual result**

On Windows, extension installation can fail after successful extraction when a reader briefly holds a file or directory inside the staging directory open. The final `os.rename(staging, installed)` returns `WinError 5`, and the installer immediately reports failure before the extension is imported.

In the controlled reproduction, the staging directory exists, the destination does not exist, and the child file is opened with `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`. Closing that owned handle makes the rename possible. A local bounded-retry experiment completes the same installation after a short wait.

This was first encountered intermittently while installing into a disposable extension repository inside a development workspace. One zero-loss FileIO trace captured 3 failed installations out of 12 ordinary-user attempts. The attached standalone reproduction removes the large extension package and the editor from the required setup.

The user-visible effect is a failed extension installation. During an update, the existing implementation may already have removed or relocated the previous version before this rename, so the extension can be left unavailable. Already-installed extension execution is outside the failing step.

**Expected result**

Please consider a bounded recovery path for a transient staging-directory rename failure, while retaining a clear failure for persistent permission problems, long-lived readers, or an occupied destination. The Windows restriction itself is not the bug being reported; the concern is installation recovery from brief, recoverable contention.

**Local recovery experiment**

A local patch retries only Windows `WinError 5`, while the source is still a directory and the destination is absent. It waits 50/100/200/400/800 ms, for at most six native rename calls and 1.55 seconds of intentional waiting. It checks source/destination again after each wait, honors cancellation, and preserves failure for other errors or persistent denial. It does not bypass permissions or close another process's handles.

Actual results from the attached standalone script, on both 5.1.1 and 5.2.2:

| Condition | Original installer | Local retry experiment |
| --- | --- | --- |
| No child handle | Installed; one successful rename | Installed; one successful rename |
| Brief child file handle | Failed; one real `WinError 5`; no installed manifest | Installed; first native attempt failed, second succeeded after the first 50 ms wait |

There are eight runs in the attached JSON: two versions, original/patched, clean/held. `installation_status` records the actual install result; `reproduction_check` records whether the observed result matches the stated experiment. A successful reproduction check does not turn a failed original installation into a successful one.

Separate tests exercised child-directory handles, persistent contention, reinstall, cancellation and path changes. Persistent contention still failed after the retry limit. Boundary-condition errors were explicitly injected in those additional branch tests; the main reproduction above uses a real native file-handle failure. Background Blender installation, enablement and reinstallation also passed with the local patch. These results do not constitute manual GUI-click acceptance or a daily-build test.

The retry proposal does not add transactional rollback of the previous extension version, and does not claim to fix all causes of `WinError 5`.

**Related report and evidence limits**

The source comment references [#130211](https://projects.blender.org/blender/blender/issues/130211). Its associated [fix `f03fba614d`](https://github.com/blender/blender/commit/f03fba614d354c0a3a5d952798803715488679e6) added rename error handling and handling of an existing file at the destination. That change does not add a retry for a short-lived child reader. This report supplies that controlled reproduction and recovery experiment; please link or merge it with an existing report if appropriate.

Historical traces recorded Pylance and Codex desktop access overlapping some failures. Successful cases also had nearby reader activity. These observations support investigation of timing-dependent contention but do not establish that either application caused every failure, nor identify a kernel filter or antivirus product responsible for a particular result. The standalone test establishes the behavior of an intentionally held real handle, not the identity of a historical reader.

The raw ETL includes unrelated machine/process information and is retained locally. The attached summary contains the installer hashes, minimal reproduction results and expected outcomes needed to assess this report. The full tracker discussion and a complete duplicate search were not accessible during preparation.

The recorded reproductions are installation failures, not Blender crashes. The attached JSON contains the error and installation results; no crash dump was produced.

### Steps to Reproduce the Issue

No `.blend` file is required: the failure occurs in the standalone extension installer before any scene or extension is loaded. The reproduction does not depend on startup-file contents. The script creates a minimal valid extension ZIP containing an empty register/unregister implementation and one child text file.

1. Extract the attached ZIP into a writable working directory. It contains `native_rename_repro.py` and `native-extension-rename-repro.json`.
2. Use an **unmodified** Blender installer file. The script reads it without changing Blender's installation or user preferences.
3. Open PowerShell in that directory and run the control followed by the held-child case. Each work-directory name must be unused:

```powershell
$python = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
$installer = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\scripts\addons_core\bl_pkg\cli\blender_ext.py'

# Each --work directory must be new. The script refuses to reuse an existing one.
# Control: no child handle, expected successful installation and exit code 0.
& $python -I -S -B .\native_rename_repro.py `
    --installer $installer --blender-version 5.2.2 --work .\rename-clean

# Reproduction: a real short-lived child handle, expected failure on the original installer.
& $python -I -S -B .\native_rename_repro.py `
    --installer $installer --blender-version 5.2.2 --work .\rename-held --hold-child
```

4. Compare the two `result.json` files. The control installs successfully. On the original installer, the held-child run returns exit code 1, has no installed manifest, and records the following fields:

```json
{
  "installer_return": false,
  "manifest_matches": false,
  "rename_attempts": [
    {
      "source_exists": true,
      "destination_exists": false,
      "status": "Failed",
      "winerror": 5
    }
  ]
}
```

The installer also emits `Failed to rename directory for "rename_issue_fixture"` with `WinError 5`. The localized Windows error text and work-directory paths vary by machine.

5. To repeat on 5.1.1, use its matching bundled Python and installer paths and `--blender-version 5.1.1`, with new work-directory names. Work directories are retained for inspection.

**How the controlled reproduction works**

The script loads the original file with `runpy`, then calls `subcmd_client._install_package_from_file_impl` on the generated ZIP. To control the timing, it temporarily wraps `os.rename` in this disposable diagnostic process. Immediately before the first staging-to-destination call, it opens a real child file handle, then calls the real `os.rename`. It does **not** inject an exception or replace the filesystem operation with a fake result. After the first native failure, it schedules the handle to close after 20 ms; the measured release delay is recorded in the JSON. The wrapper is restored and only the handle it owns is closed.
````

# Submission note

建议提交。新增价值是两版原版安装器的独立确定性复现、真实子句柄和原版/修复对照；维护者可能将有限重试视为健壮性改进，是否按 bug 或 enhancement 接收由上游判断。

标题填写上方 **Issue title**。正文已经按网页的四个栏目排列，可整体复制 **Issue body** 内的英文内容，或将各节分别粘贴到对应栏目；不要复制网页的 Instructions、Help the developers 提示，也不要把本节中文说明复制进正文。提交目标是 [Blender 源码仓库 Issues](https://projects.blender.org/blender/blender/issues)，不是 MCP 插件仓库。

提交前先查看 [#130211](https://projects.blender.org/blender/blender/issues/130211)，并同时搜索开放和关闭的问题，例如 `Failed to rename directory`、`WinError 5`、`extension install`。已确认相关旧提交和当前源码，但 tracker 正文访问受限，尚未排除重复；若已有报告正在跟进同一触发条件，将本文作为补充证据。

在网页的 Drop files here 区域上传已准备的[附件 ZIP](../../build/latest/native-extension-rename-issue-attachments.zip)。其中包含以下两份已实际运行并核验的附件；脚本会自行生成最小扩展 ZIP，复现不需要 `.blend`、MCP 插件包或原始 ETL：

- [native_rename_repro.py](attachments/native_rename_repro.py)：独立标准库复现脚本。
- [native-extension-rename-repro.json](evidence/native-extension-rename-repro.json)：八次实际运行结果，绑定原版/修复安装器和脚本 SHA-256。

你本机的两版系统安装器已经打过补丁。若你自己复跑英文正文命令验证原版故障，应将 `$installer` 改为仓库保留的原版文件，例如 `build/latest/native-install-fix/blender-5.2.2/blender_ext.original.py` 的绝对路径；不必为了报告而还原系统文件。维护者使用干净的官方安装则可直接使用正文路径。

当前未运行最新 daily build，也未完成独立 GUI 点击复现，正文已明确标出。可通过 Blender 的 `Help > Report a Bug` 补入当前系统信息；不要把本地修复版本填写为已知正常的官方版本。官方要求见[有效 bug 报告指南](https://developer.blender.org/docs/handbook/bug_reports/making_good_bug_reports/)，去重和源码依据见[研究记录](../../.scratch/mcp-tool-reliability/native-rename-upstream-research.md)。

状态：已提交为 [Blender #165012](https://projects.blender.org/blender/blender/issues/165012)（2026-10-11，Type/Bug、Severity/Normal、Status/Needs Triage）；附件 ZIP 已随 issue 上传。若上游有新结论，更新本节并补充对应回复。
