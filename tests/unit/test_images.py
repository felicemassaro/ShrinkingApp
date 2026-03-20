from __future__ import annotations

import unittest
from pathlib import Path

from shrinkingapp.models import CompressionKind
from shrinkingapp.system.images import normalize_output_image_path


class NormalizeOutputImagePathTests(unittest.TestCase):
    def test_in_place_uses_source_image(self) -> None:
        source = Path("/tmp/source.img")
        self.assertEqual(
            normalize_output_image_path(source, None, None),
            source,
        )

    def test_removes_gzip_suffix_before_processing(self) -> None:
        source = Path("/tmp/source.img")
        output = Path("/tmp/output.img.gz")
        self.assertEqual(
            normalize_output_image_path(source, output, CompressionKind.GZIP),
            Path("/tmp/output.img").resolve(),
        )

    def test_removes_xz_suffix_before_processing(self) -> None:
        source = Path("/tmp/source.img")
        output = Path("/tmp/output.img.xz")
        self.assertEqual(
            normalize_output_image_path(source, output, CompressionKind.XZ),
            Path("/tmp/output.img").resolve(),
        )


if __name__ == "__main__":
    unittest.main()
