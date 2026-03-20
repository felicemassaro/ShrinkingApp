from __future__ import annotations

import unittest
from pathlib import Path

from shrinkingapp.system.partitions import parse_parted_machine_output, partition_kind, select_shrink_partition


class ParsePartedMachineOutputTests(unittest.TestCase):
    def test_parses_msdos_layout(self) -> None:
        output = """\
BYT;
/tmp/test.img:4026531840B:file:512:512:msdos::;
1:4194304B:71303167B:67108864B:fat32::lba;
2:71303168B:4026531839B:3955228672B:ext4::;
"""
        layout = parse_parted_machine_output(Path("/tmp/test.img"), output)
        self.assertEqual(layout.partition_table, "msdos")
        self.assertEqual(layout.logical_sector_size, 512)
        self.assertEqual(len(layout.partitions), 2)
        self.assertEqual(layout.partitions[-1].filesystem, "ext4")

    def test_selects_last_partition_for_shrink(self) -> None:
        output = """\
BYT;
/tmp/test.img:4026531840B:file:512:512:gpt::;
1:1048576B:71303167B:70254592B:fat32::boot, esp;
2:71303168B:4026531839B:3955228672B:ext4::;
"""
        layout = parse_parted_machine_output(Path("/tmp/test.img"), output)
        partition = select_shrink_partition(layout)
        self.assertEqual(partition.number, 2)
        self.assertEqual(partition.start_bytes, 71303168)

    def test_detects_logical_partition_by_number(self) -> None:
        output = """\
BYT;
/tmp/test.img:4026531840B:file:512:512:msdos::;
5:71303168B:4026531839B:3955228672B:ext4::;
"""
        layout = parse_parted_machine_output(Path("/tmp/test.img"), output)
        self.assertEqual(partition_kind(layout, layout.partitions[0]), "logical")


if __name__ == "__main__":
    unittest.main()
