from __future__ import annotations

import sys

from PySide6 import QtCore, QtGui, QtWidgets

from shrinkingapp.ui.controller import JobProcessController
from shrinkingapp.ui.theme import APP_STYLESHEET
from shrinkingapp.ui.widgets import CapturePage, JobMonitorWidget, RestorePage, ShrinkPage


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ShrinkingApp")
        self.resize(1240, 840)

        self._controller = JobProcessController(self)

        shell = QtWidgets.QFrame()
        shell.setObjectName("MainShell")
        self.setCentralWidget(shell)

        root = QtWidgets.QHBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        nav = QtWidgets.QFrame()
        nav.setObjectName("NavRail")
        nav.setFixedWidth(230)
        nav_layout = QtWidgets.QVBoxLayout(nav)
        nav_layout.setContentsMargins(20, 24, 20, 24)
        nav_layout.setSpacing(10)

        title = QtWidgets.QLabel("ShrinkingApp")
        title.setObjectName("NavTitle")
        subtitle = QtWidgets.QLabel("Capture, shrink, and restore Raspberry Pi images.")
        subtitle.setObjectName("NavSubtitle")
        subtitle.setWordWrap(True)
        nav_layout.addWidget(title)
        nav_layout.addWidget(subtitle)

        self._nav_list = QtWidgets.QListWidget()
        self._nav_list.setObjectName("NavList")
        self._nav_list.addItems(["Capture", "Shrink", "Restore"])
        self._nav_list.setCurrentRow(0)
        nav_layout.addWidget(self._nav_list, 1)

        content = QtWidgets.QWidget()
        content.setObjectName("ContentArea")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(18)

        self._stack = QtWidgets.QStackedWidget()
        self._capture_page = CapturePage()
        self._shrink_page = ShrinkPage()
        self._restore_page = RestorePage()
        self._stack.addWidget(self._capture_page)
        self._stack.addWidget(self._shrink_page)
        self._stack.addWidget(self._restore_page)

        self._monitor = JobMonitorWidget()

        content_layout.addWidget(self._stack, 2)
        content_layout.addWidget(self._monitor, 1)

        root.addWidget(nav)
        root.addWidget(content, 1)

        self.statusBar().showMessage("Ready")

        self._nav_list.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._capture_page.run_requested.connect(self._start_job)
        self._shrink_page.run_requested.connect(self._start_job)
        self._restore_page.run_requested.connect(self._start_job)
        self._monitor.abort_requested.connect(self._request_abort)

        self._controller.job_started.connect(self._on_job_started)
        self._controller.job_phase.connect(self._monitor.set_phase)
        self._controller.job_log.connect(self._monitor.append_log)
        self._controller.job_progress.connect(self._monitor.update_progress)
        self._controller.job_finished.connect(self._on_job_finished)
        self._controller.job_running_changed.connect(self._set_running_state)

    def _start_job(self, payload: dict[str, object]) -> None:
        self.statusBar().showMessage("Waiting for backend authorization...")
        self._monitor.start_job(
            str(payload["title"]),
            total_bytes=payload.get("total_bytes"),
        )
        self._monitor.append_log(str(payload.get("details", "")))
        self._controller.start_job(
            title=str(payload["title"]),
            cli_args=list(payload["cli_args"]),
            total_bytes=payload.get("total_bytes"),
        )

    def _on_job_started(self, title: str) -> None:
        self.statusBar().showMessage(f"{title} running")

    def _on_job_finished(self, success: bool, summary: object, error_text: str, aborted: bool) -> None:
        self._monitor.finish(
            success,
            summary if isinstance(summary, dict) else None,
            error_text,
            aborted=aborted,
        )
        if aborted:
            self.statusBar().showMessage("Job aborted")
            return

        self.statusBar().showMessage("Job completed" if success else "Job failed")
        if not success:
            QtWidgets.QMessageBox.critical(
                self,
                "Backend Job Failed",
                error_text or "The backend command failed. Check the log monitor for details.",
            )

    def _request_abort(self) -> None:
        if not self._controller.is_running():
            return
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Warning)
        dialog.setWindowTitle("Abort Current Job")
        dialog.setText("Stop the current backend job?")
        dialog.setInformativeText("The current operation will be interrupted. Partial output files may remain on disk.")
        dialog.setStandardButtons(QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Yes)
        dialog.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        if dialog.exec() != QtWidgets.QMessageBox.Yes:
            return
        self.statusBar().showMessage("Aborting current job...")
        self._controller.abort_job()

    def _set_running_state(self, running: bool) -> None:
        self._capture_page.setEnabled(not running)
        self._shrink_page.setEnabled(not running)
        self._restore_page.setEnabled(not running)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("ShrinkingApp")
    app.setWindowIcon(QtGui.QIcon.fromTheme("drive-removable-media"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
