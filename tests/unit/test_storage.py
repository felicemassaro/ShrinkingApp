from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from shrinkingapp.models import EndpointCapability
from shrinkingapp.system.storage import discover_storage_locations


class DiscoverStorageLocationsTests(unittest.TestCase):
    def test_includes_parallels_shared_folder_when_probe_permissions_look_broken(self) -> None:
        shared_path = Path("/media/psf/Felices_SSD")

        def fake_exists(path: Path) -> bool:
            return str(path) in {"/media/psf", "/media", "/mnt"}

        def fake_is_dir(path: Path) -> bool:
            return str(path) in {"/media/psf", "/media", "/mnt"}

        def fake_iterdir(path: Path):
            if str(path) == "/media/psf":
                return iter([shared_path])
            return iter([])

        with (
            mock.patch("shrinkingapp.system.storage.Path.home", return_value=Path("/home/parallels")),
            mock.patch("pathlib.Path.exists", autospec=True, side_effect=fake_exists),
            mock.patch("pathlib.Path.is_dir", autospec=True, side_effect=fake_is_dir),
            mock.patch("pathlib.Path.iterdir", autospec=True, side_effect=fake_iterdir),
            mock.patch("shrinkingapp.system.storage._probe_directory", return_value=(False, False)),
        ):
            locations = discover_storage_locations()

        selected = next((location for location in locations if location.path == shared_path), None)
        self.assertIsNotNone(selected)
        self.assertIn(EndpointCapability.READABLE, selected.capabilities)
        self.assertIn(EndpointCapability.WRITABLE, selected.capabilities)
        self.assertIn(EndpointCapability.BROWSABLE, selected.capabilities)
        self.assertIn(EndpointCapability.EXTERNAL, selected.capabilities)


if __name__ == "__main__":
    unittest.main()
