# Windows extension staging-directory rename intermittently fails with WinError 5

Target: [Blender host issue tracker](https://projects.blender.org/blender/blender/issues). Prepared locally, not submitted. The installer's comment references #130211; its contents could not be checked because the tracker returned HTTP 403.

## Environment and scope

Windows x64, Blender 5.1.1 / bundled Python 3.13.9 and Blender 5.2.2 LTS / bundled Python 3.13.13. A platform-matching extension ZIP is installed into a disposable local repository inside an open development workspace. The failure occurs before the extension is imported or its MCP server starts.

The unchanged `bl_pkg/cli/blender_ext.py` performs `os.rename(staging, installed)` after extraction. On 5.2.2 this is line 4147. The source exists and the destination is absent. The error is `Failed to rename directory ... [WinError 5] Access is denied`. Temporary extraction is then removed.

The wrapper runs this original file through `runpy` in the bundled `python.exe -I -S -B`, observing the rename in a disposable process. Program Files, user Blender preferences and security settings remain unchanged.

## Reproduction

From a workspace visible to editor/indexing processes, repeat native `install-files` into a fresh local directory with the matching bundled Python and a valid ZIP. The setup and exact package hashes are in [the diagnostic report](../native-install-diagnosis.md) and [MCP checks](../mcp-tool-checks.md).

```powershell
$python = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'
$installer = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\scripts\addons_core\bl_pkg\cli\blender_ext.py'

# Use a new owned directory for each run. Verify the installed manifest;
# process exit code alone did not reliably indicate installation success.
& $python -I -S -B $installer install-files '<matching-extension.zip>' --local-dir '<fresh-local-repository>' --blender-version 5.2.2 --python-version 3.13.13
```

This is intermittent. In the recorded ordinary-token series, 3 of 12 installs failed. A separate 5.1 series also captured failures.

## Captured evidence

The second WPR run elevated only the recorder; all installer workers remained non-administrative. FileIO Rename / OperationEnd captured `STATUS_ACCESS_DENIED (0xC0000022)` for installer PIDs 28056, 72656 and 14780.

- Case 1: Pylance PID 135884 opened a child RST document 3.6 microseconds before the rename. Cleanup followed 8.8034 milliseconds after rename start, later than its denied completion.
- Case 5: Codex desktop PID 150648 opened the `_vendor` child directory 22.8 microseconds before rename. Cleanup followed 64.3 microseconds after start; the denied operation ended at 206.5 microseconds.
- Case 12: no remaining external child object was captured at rename start. Its exact holder is unconfirmed.

The second trace reports 2553 lost events. Cleaned file objects awaiting final Close and failed opens are not treated as live user handles. Some successful cases also have nearby editor activity; mere activity does not establish causation. Captured filter callback addresses map to `fileinfo.sys`, without final return-status attribution. No antivirus attribution is claimed.

A third, separately authorized recording reduced unrelated providers and stacks. It again used 12 ordinary-token installers, without retry. Cases 3, 5 and 8 failed in Python and had no installed manifest; the other nine completed. xperf reports zero lost events and zero lost buffers. The recorder is stopped.

For each actual failure, Codex desktop `ChatGPT.exe` PID 150648 successfully opened a child directory during the rename interval (share mask 7):

| Case | Child | Open after Rename start | Cleanup after start | Associated FileIo OpEnd |
| --- | --- | --- | --- | --- |
| 3 | `_vendor` | 57.1 us | 111.0 us | 90.5 us, `0xC0000022` |
| 5 | `_vendor` | 109.5 us | 180.6 us | 134.9 us, `0xC0000022` |
| 8 | `_vendor/runtime` | 83.3 us | 948.5 us | 936.7 us, `0xC0000022` |

Case 3 had no uncleaned external child object at Rename start. An inventory limited to the start instant would miss its later open. This strengthens the transient workspace-reader explanation, without identifying the holder in the second trace's historical case 12.

Two successful installations, cases 4 and 7, also have an associated FileIo OpEnd with `0xC0000022`. Case 4 was independently decoded with xperf, including its stack. The event is logged on the `fileinfo.sys` postoperation path; it is not a complete record of subsequent upper-filter processing. These are retained as local event observations, not counted as additional failed installations or attributed to a particular driver. Caller outcome and event outcome are separate fields in the analysis. The exact reason for the later successful Win32 outcome is unconfirmed.

A controlled Win32 experiment separately opened either a child file or child directory with share masks 3 and 7. Parent DELETE access succeeded, but parent rename failed with WinError 5 until the owned child handle closed. It matches the directory-open-file restriction in Microsoft's [FileRenameInformation specification](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/87f86c9b-6c2a-4803-84b7-131a74a434fa).

## Expected behavior and tested recovery direction

An installer should report the failure reliably and avoid treating an incomplete installation as usable. A short-lived external reader should have a bounded recovery path where safe.

A diagnostic-only retry around the original rename checked WinError 5, source-directory existence and destination absence, then used waits of 50/100/200/400/800 milliseconds. In 12 ordinary-token runs on each host, all 24 installations completed; 5.1 had one first-attempt failure and 5.2 had two. All three recovered on the first 50-millisecond retry. Reports still label those first attempts Failed.

This is evidence for a bounded recovery proposal, not a production patch or proof all WinError 5 failures are transient. Persistent permission failures, occupied destinations and other errors must remain failures. Upgrade rollback behavior and a host patch require separate validation.

## Local evidence

- `native-rename-trace-5.2-external-tests.json`, `findings.json`, `rename-context.json`
- `native-rename-trace-5.2-external-focused-tests.json`, latest `findings.json`, `rename-context.json`, `worker-windows.json`, `case-4-events.csv`, and zero-loss `trace-statistics.txt`
- Latest focused byte-verified `native-install.etl.gz`, retained locally; decompress before WPA inspection. Earlier full traces are retired with original/archive hashes and compact findings preserved
- `windows-rename-contract-tests.json`
- `windows-rename-sections-tests.json`: six successful renames while a child process retained only a data mapping, ruling out that narrow mapping-only explanation
- `native-rename-5.1-bounded-retry-tests.json` and `native-rename-5.2-bounded-retry-tests.json`

Raw ETL may include unrelated system/process data and should be reviewed before sharing. The relevant compact context and hashes can be supplied first. No external handles were forcibly closed and no security settings were changed.
