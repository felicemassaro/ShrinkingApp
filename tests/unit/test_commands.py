from __future__ import annotations

import unittest
from unittest import mock

from shrinkingapp.system.commands import CommandResult, detect_tool_versions


class DetectToolVersionsTests(unittest.TestCase):
    def test_skips_nonzero_version_probe_results(self) -> None:
        responses = [
            CommandResult(args=["e2fsck", "--version"], returncode=1, stdout="", stderr="invalid option"),
            CommandResult(args=["e2fsck", "-V"], returncode=0, stdout="", stderr="e2fsck 1.47.0"),
        ]

        with mock.patch("shrinkingapp.system.commands.run_command", side_effect=responses):
            versions = detect_tool_versions(["e2fsck"])

        self.assertEqual(versions["e2fsck"], "e2fsck 1.47.0")


if __name__ == "__main__":
    unittest.main()

