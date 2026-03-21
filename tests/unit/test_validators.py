from __future__ import annotations

import unittest
from unittest import mock
from pathlib import Path

from shrinkingapp.core.validators import validate_block_device, validate_output_path, validate_source_image


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


if __name__ == "__main__":
    unittest.main()
