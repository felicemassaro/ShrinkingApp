from __future__ import annotations

import unittest
from pathlib import Path

from shrinkingapp.system.devices import parse_lsblk_json


class ParseLsblkJsonTests(unittest.TestCase):
    def test_parses_disk_and_partition_tree(self) -> None:
        payload = """\
{
  "blockdevices": [
    {
      "name": "sdb",
      "path": "/dev/sdb",
      "size": 63864569856,
      "model": "Apple SDXC Reader",
      "tran": "usb",
      "rm": true,
      "ro": false,
      "type": "disk",
      "fstype": null,
      "mountpoints": [null],
      "children": [
        {
          "name": "sdb1",
          "path": "/dev/sdb1",
          "size": 536870912,
          "model": null,
          "tran": null,
          "rm": true,
          "ro": false,
          "type": "part",
          "fstype": "vfat",
          "mountpoints": ["/media/parallels/bootfs"]
        }
      ]
    }
  ]
}
"""
        devices = parse_lsblk_json(payload)
        self.assertEqual(len(devices), 1)
        disk = devices[0]
        self.assertEqual(disk.path, Path("/dev/sdb"))
        self.assertTrue(disk.removable)
        self.assertEqual(disk.transport, "usb")
        self.assertEqual(len(disk.children), 1)
        self.assertEqual(disk.children[0].mountpoints, ("/media/parallels/bootfs",))


if __name__ == "__main__":
    unittest.main()

