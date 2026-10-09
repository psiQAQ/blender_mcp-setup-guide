import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compact_native_trace import archive_trace, restored_digest
from inspect_native_rename_trace import main as inspect_trace, summarize_children, trace_loss_summary
from correlate_native_rename_events import process_at


class NativeTraceTests(unittest.TestCase):
    def test_open_after_rename_start_is_retained_and_caller_result_stays_separate(self):
        provider = "{90CBDC39-4A3E-11D1-84F4-0000F80464E3}"
        events = [
            (71, 42, 100, {"IrpPtr": "rename", "FileObject": "parent"}),
            (64, 99, 110, {"IrpPtr": "open", "FileObject": "child", "OpenPath":
                r"\case-1\profile\extensions\integration_test\blender_mcp_integration@\_vendor"}),
            (76, 99, 111, {"IrpPtr": "open", "NtStatus": "hex:00000000"}),
            (76, 42, 120, {"IrpPtr": "rename", "NtStatus": "hex:220000c0"}),
            (65, 99, 130, {"FileObject": "child"}),
            (66, 99, 135, {"FileObject": "child"}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exported, report, output = (root / name for name in ("events.jsonl", "report.json", "findings.json"))
            exported.write_text("".join(json.dumps({"provider": provider, "opcode": opcode,
                "pid": pid, "filetime": timestamp, "properties": properties}, separators=(",", ":")) + "\n"
                for opcode, pid, timestamp, properties in events), encoding="utf-8")
            report.write_text(json.dumps({"cases": [{"case": 1, "renames": [
                {"pid": 42, "status": "Passed"}]}]}), encoding="utf-8")
            with patch.object(sys, "argv", ["inspect", str(exported), "--report", str(report), "--output", str(output)]), redirect_stdout(io.StringIO()):
                inspect_trace()
            rename = json.loads(output.read_text())["cases"][0]["rename_events"][0]
            self.assertEqual((rename["caller_status"], rename["status"]), ("Passed", "Failed"))
            self.assertEqual(rename["uncleaned_child_file_objects"], [])
            self.assertEqual(len(rename["opens_during_rename"]), 1)
            opened = rename["opens_during_rename"][0]
            self.assertEqual((opened["opened_at"], opened["cleanup_at"]), (110, 130))
            self.assertEqual(opened["open_status"], "hex:00000000")

    def test_reused_pid_resolves_the_process_alive_at_the_event(self):
        processes = {42: [
            {"filetime": 100, "properties": {"ImageFileName": "python.exe"}},
            {"filetime": 300, "properties": {"ImageFileName": "git.exe"}},
        ]}
        self.assertEqual(process_at(processes, 42, 200)["ImageFileName"], "python.exe")
        self.assertEqual(process_at(processes, 42, 400)["ImageFileName"], "git.exe")
        self.assertEqual(process_at(processes, 42, 50), {})

    def test_loss_counts_come_from_this_recording_not_a_previous_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            statistics = Path(directory) / "statistics.txt"
            statistics.write_text("Total # Lost Buffers : 0\nTotal # Lost Events : 0\n", encoding="utf-8")
            result = trace_loss_summary(statistics)
            self.assertEqual((result["events"], result["buffers"]), (0, 0))
            self.assertEqual(trace_loss_summary(None), {"events": None, "buffers": None})

    def test_missing_loss_counts_fail_instead_of_claiming_zero_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            statistics = Path(directory) / "statistics.txt"
            statistics.write_text("The trace could not be read", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing total lost"):
                trace_loss_summary(statistics)

    def test_cleanup_and_failed_opens_are_not_reported_as_live_user_handles(self):
        snapshot = {"filetime": 100, "child_file_objects": [
            {"pid": 1, "open_status": "hex:00000000", "cleanup_at": 90},
            {"pid": 2, "open_status": "hex:340000c0"},
            {"pid": 3, "open_status": None},
        ]}
        summarize_children(snapshot)
        self.assertEqual(snapshot["uncleaned_child_file_objects"], [])
        self.assertEqual(snapshot["cleaned_not_closed_counts_by_pid"], {1: 1})
        self.assertEqual(snapshot["failed_open_count"], 1)
        self.assertEqual(snapshot["unknown_open_count"], 1)

    def test_cleanup_after_rename_preserves_the_overlapping_open(self):
        opened = {"pid": 42, "open_status": "hex:00000000", "cleanup_at": 150, "closed_at": 155}
        snapshot = {"filetime": 100, "child_file_objects": [opened]}
        summarize_children(snapshot)
        self.assertEqual(snapshot["uncleaned_child_file_objects"], [opened])
        self.assertEqual(snapshot["cleaned_not_closed_counts_by_pid"], {})

    def test_archive_restores_original_bytes_and_keeps_source_until_explicit_retirement(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source = parent / "recording.etl"
            data = b"unaltered ETW event bytes\x00\xff" * 128
            source.write_bytes(data)
            with patch("build_cache.BUILD", parent):
                result = archive_trace(source)
            self.assertEqual(result["original_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(restored_digest(Path(result["archive"])), result["original_sha256"])
            self.assertEqual(source.read_bytes(), data)
            self.assertFalse(source.with_suffix(".etl.gz.pending").exists())

    def test_archive_refuses_to_replace_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source = parent / "recording.etl"
            archive = source.with_suffix(".etl.gz")
            source.write_bytes(b"current recording")
            archive.write_bytes(b"previous evidence")
            with patch("build_cache.BUILD", parent), self.assertRaises(FileExistsError):
                archive_trace(source)
            self.assertEqual(archive.read_bytes(), b"previous evidence")
            self.assertEqual(source.read_bytes(), b"current recording")


if __name__ == "__main__":
    unittest.main()
