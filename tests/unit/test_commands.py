from __future__ import annotations

import signal
import subprocess
import unittest
from unittest import mock

from shrinkingapp.system.commands import CommandResult, detect_tool_versions, terminate_process_tree


class DetectToolVersionsTests(unittest.TestCase):
    def test_skips_nonzero_version_probe_results(self) -> None:
        responses = [
            CommandResult(args=["e2fsck", "--version"], returncode=1, stdout="", stderr="invalid option"),
            CommandResult(args=["e2fsck", "-V"], returncode=0, stdout="", stderr="e2fsck 1.47.0"),
        ]

        with mock.patch("shrinkingapp.system.commands.run_command", side_effect=responses):
            versions = detect_tool_versions(["e2fsck"])

        self.assertEqual(versions["e2fsck"], "e2fsck 1.47.0")


class TerminateProcessTreeTests(unittest.TestCase):
    @mock.patch("shrinkingapp.system.commands.os.killpg")
    @mock.patch("shrinkingapp.system.commands.os.getpgid", return_value=4321)
    def test_sends_sigterm_to_process_group(self, mock_getpgid: mock.Mock, mock_killpg: mock.Mock) -> None:
        process = mock.Mock()
        process.pid = 1234
        process.poll.return_value = None
        process.wait.return_value = 0

        terminate_process_tree(process, grace_seconds=0.1)

        mock_getpgid.assert_called_once_with(1234)
        mock_killpg.assert_called_once_with(4321, signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=0.1)

    @mock.patch("shrinkingapp.system.commands.os.killpg")
    @mock.patch("shrinkingapp.system.commands.os.getpgid", return_value=4321)
    def test_escalates_to_sigkill_after_timeout(self, mock_getpgid: mock.Mock, mock_killpg: mock.Mock) -> None:
        process = mock.Mock()
        process.pid = 1234
        process.poll.return_value = None
        process.wait.side_effect = subprocess.TimeoutExpired(cmd="sleep", timeout=0.1)

        terminate_process_tree(process, grace_seconds=0.1)

        self.assertEqual(
            mock_killpg.call_args_list,
            [
                mock.call(4321, signal.SIGTERM),
                mock.call(4321, signal.SIGKILL),
            ],
        )


if __name__ == "__main__":
    unittest.main()
