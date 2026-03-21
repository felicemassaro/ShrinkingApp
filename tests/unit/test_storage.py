from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from shrinkingapp.models import EndpointCapability, EndpointKind, StorageEndpoint
from shrinkingapp.system.commands import CommandResult
from shrinkingapp.system.storage import describe_storage_path, discover_storage_locations


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

    def test_describe_storage_path_uses_mount_and_backing_disk_metadata(self) -> None:
        output_path = Path("/media/parallels/bootfs/pi-source.img")
        endpoint = StorageEndpoint(
            label="Mounted: bootfs",
            path=Path("/media/parallels/bootfs"),
            kind=EndpointKind.FILESYSTEM,
            capabilities=frozenset(
                {
                    EndpointCapability.READABLE,
                    EndpointCapability.WRITABLE,
                    EndpointCapability.BROWSABLE,
                    EndpointCapability.EXTERNAL,
                }
            ),
        )
        findmnt_payload = """\
{"filesystems":[{"target":"/media/parallels/bootfs","source":"/dev/sde1","fstype":"vfat","size":"536870912","avail":"468713472"}]}
"""

        with (
            mock.patch("shrinkingapp.system.storage.discover_storage_locations", return_value=[endpoint]),
            mock.patch(
                "shrinkingapp.system.storage.run_command",
                return_value=CommandResult(
                    args=["findmnt"],
                    returncode=0,
                    stdout=findmnt_payload,
                    stderr="",
                ),
            ),
            mock.patch("shrinkingapp.system.storage.get_parent_disk") as get_parent_disk,
        ):
            get_parent_disk.return_value.path = Path("/dev/sde")
            get_parent_disk.return_value.model = "SD"
            get_parent_disk.return_value.size_bytes = 15836643328
            context = describe_storage_path(output_path)

        self.assertEqual(context.location_label, "Mounted: bootfs")
        self.assertEqual(context.mount_point, Path("/media/parallels/bootfs"))
        self.assertEqual(context.mount_source, "/dev/sde1")
        self.assertEqual(context.filesystem_type, "vfat")
        self.assertEqual(context.total_bytes, 536870912)
        self.assertEqual(context.free_bytes, 468713472)
        self.assertEqual(context.backing_disk_path, Path("/dev/sde"))
        self.assertEqual(context.backing_disk_model, "SD")

    def test_describe_storage_path_falls_back_to_disk_usage(self) -> None:
        output_path = Path("/media/psf/Felices_SSD/result.img")
        endpoint = StorageEndpoint(
            label="Shared: Felices_SSD",
            path=Path("/media/psf/Felices_SSD"),
            kind=EndpointKind.FILESYSTEM,
            capabilities=frozenset(
                {
                    EndpointCapability.READABLE,
                    EndpointCapability.WRITABLE,
                    EndpointCapability.BROWSABLE,
                    EndpointCapability.EXTERNAL,
                }
            ),
        )

        with (
            mock.patch("shrinkingapp.system.storage.discover_storage_locations", return_value=[endpoint]),
            mock.patch(
                "shrinkingapp.system.storage.run_command",
                return_value=CommandResult(args=["findmnt"], returncode=1, stdout="", stderr=""),
            ),
            mock.patch("shrinkingapp.system.storage.shutil.disk_usage") as disk_usage,
        ):
            disk_usage.return_value = (1_000_000_000, 400_000_000, 600_000_000)
            context = describe_storage_path(output_path)

        self.assertEqual(context.location_label, "Shared: Felices_SSD")
        self.assertEqual(context.total_bytes, 1_000_000_000)
        self.assertEqual(context.free_bytes, 600_000_000)


if __name__ == "__main__":
    unittest.main()
