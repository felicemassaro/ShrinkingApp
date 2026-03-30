from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from shrinkingapp.models import EndpointCapability, EndpointKind, StorageEndpoint
from shrinkingapp.system.endpoints import discover_endpoints


class DiscoverEndpointsTests(unittest.TestCase):
    def test_filters_endpoints_by_capability_and_kind(self) -> None:
        device_endpoints = [
            StorageEndpoint(
                label="/dev/sde",
                path=Path("/dev/sde"),
                kind=EndpointKind.BLOCK_DEVICE,
                capabilities=frozenset(
                    {
                        EndpointCapability.READABLE,
                        EndpointCapability.WRITABLE,
                        EndpointCapability.REMOVABLE,
                        EndpointCapability.EXTERNAL,
                    }
                ),
                size_bytes=64,
            )
        ]
        filesystem_endpoints = [
            StorageEndpoint(
                label="Shared: Shared_SSD",
                path=Path("/media/psf/Shared_SSD"),
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
        ]

        with (
            mock.patch("shrinkingapp.system.endpoints.list_device_endpoints", return_value=device_endpoints),
            mock.patch("shrinkingapp.system.endpoints.discover_storage_locations", return_value=filesystem_endpoints),
        ):
            writable_locations = discover_endpoints(
                required_capabilities=(EndpointCapability.WRITABLE, EndpointCapability.BROWSABLE),
                allowed_kinds=(EndpointKind.FILESYSTEM,),
            )

        self.assertEqual(writable_locations, filesystem_endpoints)

    def test_deduplicates_endpoints_by_kind_and_path(self) -> None:
        duplicate = StorageEndpoint(
            label="Home",
            path=Path("/home/parallels"),
            kind=EndpointKind.FILESYSTEM,
            capabilities=frozenset(
                {
                    EndpointCapability.READABLE,
                    EndpointCapability.WRITABLE,
                    EndpointCapability.BROWSABLE,
                }
            ),
        )

        with (
            mock.patch("shrinkingapp.system.endpoints.list_device_endpoints", return_value=[]),
            mock.patch("shrinkingapp.system.endpoints.discover_storage_locations", return_value=[duplicate, duplicate]),
        ):
            endpoints = discover_endpoints(
                required_capabilities=(EndpointCapability.READABLE,),
                allowed_kinds=(EndpointKind.FILESYSTEM,),
            )

        self.assertEqual(endpoints, [duplicate])

    def test_block_device_queries_do_not_probe_filesystem_locations(self) -> None:
        device_endpoint = StorageEndpoint(
            label="/dev/sde",
            path=Path("/dev/sde"),
            kind=EndpointKind.BLOCK_DEVICE,
            capabilities=frozenset(
                {
                    EndpointCapability.READABLE,
                    EndpointCapability.WRITABLE,
                    EndpointCapability.REMOVABLE,
                }
            ),
        )

        with (
            mock.patch("shrinkingapp.system.endpoints.list_device_endpoints", return_value=[device_endpoint]) as list_devices,
            mock.patch("shrinkingapp.system.endpoints.discover_storage_locations") as list_locations,
        ):
            endpoints = discover_endpoints(
                required_capabilities=(EndpointCapability.READABLE,),
                allowed_kinds=(EndpointKind.BLOCK_DEVICE,),
            )

        self.assertEqual(endpoints, [device_endpoint])
        list_devices.assert_called_once()
        list_locations.assert_not_called()

    def test_filesystem_queries_do_not_probe_block_devices(self) -> None:
        filesystem_endpoint = StorageEndpoint(
            label="Home",
            path=Path("/home/parallels"),
            kind=EndpointKind.FILESYSTEM,
            capabilities=frozenset(
                {
                    EndpointCapability.READABLE,
                    EndpointCapability.WRITABLE,
                    EndpointCapability.BROWSABLE,
                }
            ),
        )

        with (
            mock.patch("shrinkingapp.system.endpoints.list_device_endpoints") as list_devices,
            mock.patch("shrinkingapp.system.endpoints.discover_storage_locations", return_value=[filesystem_endpoint]) as list_locations,
        ):
            endpoints = discover_endpoints(
                required_capabilities=(EndpointCapability.READABLE,),
                allowed_kinds=(EndpointKind.FILESYSTEM,),
            )

        self.assertEqual(endpoints, [filesystem_endpoint])
        list_locations.assert_called_once()
        list_devices.assert_not_called()


if __name__ == "__main__":
    unittest.main()
