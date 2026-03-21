from __future__ import annotations

import stat
import unittest
from unittest import mock
from pathlib import Path

from shrinkingapp.core.validators import (
    resolve_capture_source,
    validate_block_device,
    validate_output_path,
    validate_source_image,
)
from shrinkingapp.models import CaptureSourceKind


class ValidatorsTests(unittest.TestCase):
    def test_validate_source_image_rejects_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            validate_source_image(Path("/tmp/does-not-exist.img"))

    def test_validate_output_path_creates_parent_directory(self) -> None:
        output = Path("/tmp/nested/result.img")
        with mock.patch.object(Path, "mkdir") as mkdir:
            resolved = validate_output_path(output)
        mkdir.assert_called_once_with(parents=True, exist_ok=True)
        self.assertEqual(resolved.name, "result.img")

    def test_validate_block_device_rejects_regular_file(self) -> None:
        with mock.patch.object(Path, "stat") as mocked_stat:
            mocked_stat.return_value.st_mode = 0o100644
            with self.assertRaises(ValueError):
                validate_block_device(Path("/dev/not-a-block-device"))

    def test_resolve_capture_source_accepts_regular_file(self) -> None:
        with mock.patch.object(Path, "stat") as mocked_stat:
            mocked_stat.return_value.st_mode = stat.S_IFREG
            resolved, kind = resolve_capture_source(Path("/tmp/source.img"))
        self.assertEqual(kind, CaptureSourceKind.IMAGE_FILE)
        self.assertEqual(resolved, Path("/tmp/source.img").resolve())

    def test_resolve_capture_source_accepts_block_device(self) -> None:
        with mock.patch.object(Path, "stat") as mocked_stat:
            mocked_stat.return_value.st_mode = stat.S_IFBLK
            resolved, kind = resolve_capture_source(Path("/dev/sde"))
        self.assertEqual(kind, CaptureSourceKind.BLOCK_DEVICE)
        self.assertEqual(resolved, Path("/dev/sde").resolve())


if __name__ == "__main__":
    unittest.main()
