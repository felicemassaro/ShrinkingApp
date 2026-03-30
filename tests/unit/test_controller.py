from __future__ import annotations

import unittest

try:
    from PySide6 import QtCore
    from shrinkingapp.ui.controller import JobProcessController
except ModuleNotFoundError:  # pragma: no cover - optional in non-UI test environments
    QtCore = None
    JobProcessController = None


@unittest.skipIf(QtCore is None or JobProcessController is None, "PySide6 is not installed")
class JobProcessControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])

    def test_dd_progress_line_emits_job_progress(self) -> None:
        controller = JobProcessController()
        progress_events: list[tuple[object, object, object, object]] = []
        controller.job_progress.connect(lambda copied, total, speed, eta: progress_events.append((copied, total, speed, eta)))
        controller._job_total_bytes = 1_000_000_000

        controller._handle_log_line("stderr: 250000000 bytes (250 MB, 238 MiB) copied, 10.0 s, 25.0 MB/s")

        self.assertEqual(len(progress_events), 1)
        copied, total, speed_bps, eta_seconds = progress_events[0]
        self.assertEqual(copied, 250_000_000)
        self.assertEqual(total, 1_000_000_000)
        self.assertEqual(speed_bps, 25_000_000.0)
        self.assertEqual(eta_seconds, 30.0)

    def test_phase_line_emits_phase_percent(self) -> None:
        controller = JobProcessController()
        percents: list[int] = []
        phases: list[tuple[str, str]] = []
        controller.job_percent.connect(percents.append)
        controller.job_phase.connect(lambda phase, detail: phases.append((phase, detail)))

        controller._handle_log_line("2026-03-30 10:00:00,000 INFO PHASE restore writing image to /dev/sde")

        self.assertEqual(phases, [("Restore", "writing image to /dev/sde")])
        self.assertEqual(percents, [])


if __name__ == "__main__":
    unittest.main()
