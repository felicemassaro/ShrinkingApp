from __future__ import annotations

from collections.abc import Iterable

from shrinkingapp.models import EndpointCapability, EndpointKind, StorageEndpoint
from shrinkingapp.system.devices import list_device_endpoints
from shrinkingapp.system.storage import discover_storage_locations


def discover_endpoints(
    *,
    required_capabilities: Iterable[EndpointCapability] = (),
    allowed_kinds: Iterable[EndpointKind] | None = None,
    logger=None,
) -> list[StorageEndpoint]:
    required = tuple(required_capabilities)
    allowed = set(allowed_kinds) if allowed_kinds is not None else None

    endpoints = [
        *list_device_endpoints(logger=logger),
        *discover_storage_locations(),
    ]

    filtered: list[StorageEndpoint] = []
    seen: set[str] = set()
    for endpoint in endpoints:
        key = f"{endpoint.kind.value}:{endpoint.path}"
        if key in seen:
            continue
        seen.add(key)
        if allowed is not None and endpoint.kind not in allowed:
            continue
        if required and not endpoint.supports(*required):
            continue
        filtered.append(endpoint)
    return filtered
