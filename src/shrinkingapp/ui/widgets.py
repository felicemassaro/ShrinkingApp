from __future__ import annotations

import math
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from shrinkingapp.models import BlockDeviceInfo, CompressionKind
from shrinkingapp.system.devices import list_block_devices
from shrinkingapp.system.storage import discover_storage_locations


def human_bytes(value: int) -> str:
    if value <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = min(int(math.log(value, 1024)), len(units) - 1)
    scaled = value / (1024 ** index)
    if index == 0:
        return f"{int(scaled)} {units[index]}"
    return f"{scaled:.1f} {units[index]}"


def _device_label(device: BlockDeviceInfo) -> str:
    model = device.model or "Removable Device"
    transport = (device.transport or "unknown").upper()
    return f"{device.path}  |  {human_bytes(device.size_bytes)}  |  {model}  |  {transport}"


class DevicePicker(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._combo = QtWidgets.QComboBox()
        self._combo.setMinimumWidth(420)
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.clicked.connect(self.refresh_devices)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._combo, 1)
        layout.addWidget(self._refresh_button)

        self.refresh_devices()

    def refresh_devices(self) -> None:
        current_path = self.current_device_path()
        self._combo.clear()
        self._combo.addItem("Select a removable device", None)
        for device in list_block_devices():
            if device.device_type != "disk" or not device.removable or device.size_bytes <= 0:
                continue
            self._combo.addItem(_device_label(device), device)

        if current_path is not None:
            for index in range(self._combo.count()):
                device = self._combo.itemData(index)
                if device is not None and device.path == current_path:
                    self._combo.setCurrentIndex(index)
                    break

    def current_device(self) -> BlockDeviceInfo | None:
        return self._combo.currentData()

    def current_device_path(self) -> Path | None:
        device = self.current_device()
        return None if device is None else device.path

    def set_enabled(self, enabled: bool) -> None:
        self._combo.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)


class FilePicker(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        mode: str,
        caption: str,
        file_filter: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._caption = caption
        self._file_filter = file_filter

        self._edit = QtWidgets.QLineEdit()
        self._browse = QtWidgets.QPushButton("Browse")
        self._browse.setObjectName("SecondaryButton")
        self._browse.clicked.connect(self._open_dialog)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._browse)

    def text(self) -> str:
        return self._edit.text().strip()

    def setText(self, text: str) -> None:
        self._edit.setText(text)

    def set_directory(self, directory: str | Path, suggested_filename: str | None = None) -> None:
        base_dir = Path(directory)
        current_text = self.text()
        if self._mode == "save":
            current_path = Path(current_text) if current_text else None
            filename = None
            if current_path is not None and current_path.name and current_path.suffix:
                filename = current_path.name
            filename = filename or suggested_filename
            self._edit.setText(str(base_dir / filename) if filename else str(base_dir))
        else:
            self._edit.setText(str(base_dir))

    def line_edit(self) -> QtWidgets.QLineEdit:
        return self._edit

    def set_enabled(self, enabled: bool) -> None:
        self._edit.setEnabled(enabled)
        self._browse.setEnabled(enabled)

    def _open_dialog(self) -> None:
        if self._mode == "open":
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                self._caption,
                self.text(),
                self._file_filter,
            )
        else:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                self._caption,
                self.text(),
                self._file_filter,
            )
        if path:
            self._edit.setText(path)


class DestinationShortcutPicker(QtWidgets.QWidget):
    location_selected = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._combo = QtWidgets.QComboBox()
        self._combo.setMinimumWidth(420)
        self._use_button = QtWidgets.QPushButton("Use Location")
        self._use_button.setObjectName("SecondaryButton")
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.setObjectName("SecondaryButton")

        self._use_button.clicked.connect(self._emit_selection)
        self._refresh_button.clicked.connect(self.refresh_locations)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._combo, 1)
        layout.addWidget(self._use_button)
        layout.addWidget(self._refresh_button)

        self.refresh_locations()

    def refresh_locations(self) -> None:
        current_path = self.current_path()
        self._combo.clear()
        self._combo.addItem("Select a destination location", None)
        for label, path in discover_storage_locations():
            self._combo.addItem(f"{label}  |  {path}", str(path))

        if current_path is not None:
            for index in range(self._combo.count()):
                path = self._combo.itemData(index)
                if path == current_path:
                    self._combo.setCurrentIndex(index)
                    break

    def current_path(self) -> str | None:
        return self._combo.currentData()

    def set_enabled(self, enabled: bool) -> None:
        self._combo.setEnabled(enabled)
        self._use_button.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)

    def _emit_selection(self) -> None:
        path = self.current_path()
        if path:
            self.location_selected.emit(path)


class JobMonitorWidget(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionCard")

        self._job_label = QtWidgets.QLabel("No job running")
        self._job_label.setObjectName("MonitorTitle")
        self._phase_label = QtWidgets.QLabel("Idle")
        self._phase_label.setObjectName("MonitorMeta")
        self._stats_label = QtWidgets.QLabel("Transferred: -, Speed: -, ETA: -")
        self._stats_label.setObjectName("MonitorMeta")
        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Waiting")
        self._log = QtWidgets.QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._total_bytes: int | None = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(self._job_label)
        layout.addWidget(self._phase_label)
        layout.addWidget(self._stats_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._log, 1)

    def start_job(self, title: str, *, total_bytes: int | None) -> None:
        self._job_label.setText(title)
        self._phase_label.setText("Waiting for backend")
        self._stats_label.setText("Transferred: -, Speed: -, ETA: -")
        self._log.clear()
        self._total_bytes = total_bytes
        if total_bytes:
            self._progress.setRange(0, 100)
            self._progress.setValue(0)
            self._progress.setFormat("0%")
        else:
            self._progress.setRange(0, 0)

    def set_phase(self, phase: str, detail: str) -> None:
        text = phase if not detail else f"{phase}  |  {detail}"
        self._phase_label.setText(text)
        if self._progress.maximum() == 0 and phase.lower() == "done":
            self._progress.setRange(0, 100)
            self._progress.setValue(100)
            self._progress.setFormat("100%")

    def append_log(self, line: str) -> None:
        self._log.appendPlainText(line)
        self._log.verticalScrollBar().setValue(self._log.verticalScrollBar().maximum())

    def update_progress(self, copied: int, total: int, speed_bps: float, eta_seconds: float) -> None:
        if total > 0:
            percent = min(100, int((copied / total) * 100))
            self._progress.setRange(0, 100)
            self._progress.setValue(percent)
            self._progress.setFormat(f"{percent}%")
        speed_text = f"{human_bytes(int(speed_bps))}/s" if speed_bps > 0 else "-"
        eta_text = "-" if eta_seconds <= 0 else f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
        self._stats_label.setText(
            f"Transferred: {human_bytes(copied)} / {human_bytes(total)}, "
            f"Speed: {speed_text}, ETA: {eta_text}"
        )

    def finish(self, success: bool, summary: dict[str, object] | None, error_text: str) -> None:
        if self._progress.maximum() == 0:
            self._progress.setRange(0, 100)
        self._progress.setValue(100 if success else 0)
        self._progress.setFormat("Completed" if success else "Failed")
        self._phase_label.setText("Completed successfully" if success else "Failed")
        if success and summary:
            interesting = []
            for key in ("output_image", "target_device", "manifest_path", "log_path"):
                value = summary.get(key)
                if value:
                    interesting.append(f"{key}: {value}")
            if interesting:
                self._log.appendPlainText("")
                self._log.appendPlainText("\n".join(interesting))
        elif not success and error_text:
            self._log.appendPlainText("")
            self._log.appendPlainText(error_text)


class WorkflowPage(QtWidgets.QWidget):
    run_requested = QtCore.Signal(object)

    def __init__(self, title: str, lead: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = QtWidgets.QLabel(title)
        self._title.setObjectName("SectionTitle")
        self._lead = QtWidgets.QLabel(lead)
        self._lead.setObjectName("SectionLead")
        self._lead.setWordWrap(True)
        self._body = QtWidgets.QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(18)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(self._title)
        root.addWidget(self._lead)
        root.addLayout(self._body, 1)

    def body_layout(self) -> QtWidgets.QVBoxLayout:
        return self._body

    def set_form_enabled(self, enabled: bool) -> None:
        for child in self.findChildren(QtWidgets.QWidget):
            if child is self:
                continue
            child.setEnabled(enabled)


class CapturePage(WorkflowPage):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            "Capture",
            "Create a raw image from a removable source device. Confirm the destination before starting.",
            parent,
        )
        self._device_picker = DevicePicker()
        self._source_note = QtWidgets.QLabel(
            "Only raw removable block devices appear here. Shared SSD folders such as /media/psf/Felices_SSD are destinations, not source devices."
        )
        self._source_note.setObjectName("SectionLead")
        self._source_note.setWordWrap(True)
        self._output_picker = FilePicker(
            mode="save",
            caption="Choose Capture Destination",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._destination_shortcuts = DestinationShortcutPicker()
        self._destination_shortcuts.location_selected.connect(self._apply_destination_location)
        self._compression = QtWidgets.QComboBox()
        self._compression.addItem("None", None)
        self._compression.addItem("gzip", CompressionKind.GZIP.value)
        self._compression.addItem("xz", CompressionKind.XZ.value)
        self._parallel = QtWidgets.QCheckBox("Use parallel compression when available")
        self._start = QtWidgets.QPushButton("Start Capture")
        self._start.clicked.connect(self._on_start)

        card = QtWidgets.QGroupBox("Capture Source And Destination")
        form = QtWidgets.QFormLayout(card)
        form.addRow("Source Device", self._device_picker)
        form.addRow("", self._source_note)
        form.addRow("Destination Location", self._destination_shortcuts)
        form.addRow("Destination Image", self._output_picker)
        form.addRow("Compression", self._compression)
        form.addRow("", self._parallel)

        self.body_layout().addWidget(card)
        self.body_layout().addStretch(1)
        self.body_layout().addWidget(self._start, 0, QtCore.Qt.AlignLeft)

    def _apply_destination_location(self, path: str) -> None:
        self._output_picker.set_directory(path, suggested_filename="pi-source.img")

    def _on_start(self) -> None:
        device = self._device_picker.current_device()
        output_path = self._output_picker.text()
        if device is None:
            QtWidgets.QMessageBox.warning(self, "Capture", "Select a removable source device first.")
            return
        if not output_path:
            QtWidgets.QMessageBox.warning(self, "Capture", "Choose a destination image path.")
            return

        compression = self._compression.currentData()
        details = [
            f"Source: {_device_label(device)}",
            f"Destination: {output_path}",
            f"Compression: {compression or 'None'}",
        ]
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Question)
        dialog.setWindowTitle("Confirm Capture Destination")
        dialog.setText("Start a new raw capture job?")
        dialog.setInformativeText("Confirm the output image destination before continuing.")
        dialog.setDetailedText("\n".join(details))
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        if dialog.exec() != QtWidgets.QMessageBox.Yes:
            return

        self.run_requested.emit(
            {
                "title": "Capture Image",
                "total_bytes": device.size_bytes,
                "cli_args": [
                    "capture",
                    str(device.path),
                    output_path,
                    *([] if compression is None else ["--compression", compression]),
                    *(["--parallel-compression"] if self._parallel.isChecked() and compression else []),
                ],
                "details": "\n".join(details),
            }
        )


class ShrinkPage(WorkflowPage):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            "Shrink",
            "Shrink a Raspberry Pi image and optionally compress it. Leaving the destination blank modifies the image in place.",
            parent,
        )
        self._image_picker = FilePicker(
            mode="open",
            caption="Choose Source Image",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._output_picker = FilePicker(
            mode="save",
            caption="Choose Shrunk Image Destination",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._destination_shortcuts = DestinationShortcutPicker()
        self._destination_shortcuts.location_selected.connect(self._apply_destination_location)
        self._compression = QtWidgets.QComboBox()
        self._compression.addItem("None", None)
        self._compression.addItem("gzip", CompressionKind.GZIP.value)
        self._compression.addItem("xz", CompressionKind.XZ.value)
        self._parallel = QtWidgets.QCheckBox("Use parallel compression when available")
        self._repair = QtWidgets.QCheckBox("Use advanced filesystem repair if needed")
        self._autoexpand = QtWidgets.QCheckBox("Enable first boot filesystem expansion")
        self._start = QtWidgets.QPushButton("Start Shrink")
        self._start.clicked.connect(self._on_start)

        card = QtWidgets.QGroupBox("Shrink Options")
        form = QtWidgets.QFormLayout(card)
        form.addRow("Source Image", self._image_picker)
        form.addRow("Destination Location", self._destination_shortcuts)
        form.addRow("Destination Image", self._output_picker)
        form.addRow("Compression", self._compression)
        form.addRow("", self._parallel)
        form.addRow("", self._repair)
        form.addRow("", self._autoexpand)

        self.body_layout().addWidget(card)
        self.body_layout().addStretch(1)
        self.body_layout().addWidget(self._start, 0, QtCore.Qt.AlignLeft)

    def _apply_destination_location(self, path: str) -> None:
        source = self._image_picker.text()
        suggested_name = "pi-shrunk.img"
        if source:
            source_path = Path(source)
            if source_path.suffix:
                suggested_name = f"{source_path.stem}-shrunk{source_path.suffix}"
            else:
                suggested_name = f"{source_path.name}-shrunk.img"
        self._output_picker.set_directory(path, suggested_filename=suggested_name)

    def _on_start(self) -> None:
        source = self._image_picker.text()
        if not source:
            QtWidgets.QMessageBox.warning(self, "Shrink", "Choose a source image first.")
            return

        output = self._output_picker.text()
        compression = self._compression.currentData()
        source_size = Path(source).stat().st_size if Path(source).exists() else None

        details = [
            f"Source: {source}",
            f"Destination: {output or 'In place'}",
            f"Compression: {compression or 'None'}",
        ]
        if not output:
            details.append("Warning: the selected image will be modified in place.")

        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Question)
        dialog.setWindowTitle("Confirm Shrink Destination")
        dialog.setText("Start the shrink job with the selected destination?")
        dialog.setInformativeText("Confirm the output path before continuing.")
        dialog.setDetailedText("\n".join(details))
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        if dialog.exec() != QtWidgets.QMessageBox.Yes:
            return

        cli_args = ["shrink", source]
        if output:
            cli_args.extend(["--output", output])
        if compression:
            cli_args.extend(["--compression", compression])
        if compression and self._parallel.isChecked():
            cli_args.append("--parallel-compression")
        if self._repair.isChecked():
            cli_args.append("--repair")
        if self._autoexpand.isChecked():
            cli_args.append("--enable-first-boot-expand")

        self.run_requested.emit(
            {
                "title": "Shrink Image",
                "total_bytes": source_size,
                "cli_args": cli_args,
                "details": "\n".join(details),
            }
        )


class RestorePage(WorkflowPage):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            "Restore",
            "Write a raw image to a removable target device. The destination confirmation is destructive and required.",
            parent,
        )
        self._image_picker = FilePicker(
            mode="open",
            caption="Choose Image To Restore",
            file_filter="Disk Images (*.img);;All Files (*)",
        )
        self._device_picker = DevicePicker()
        self._start = QtWidgets.QPushButton("Start Restore")
        self._start.setObjectName("DangerButton")
        self._start.clicked.connect(self._on_start)

        card = QtWidgets.QGroupBox("Restore Target")
        form = QtWidgets.QFormLayout(card)
        form.addRow("Source Image", self._image_picker)
        form.addRow("Target Device", self._device_picker)

        warning = QtWidgets.QLabel(
            "The selected target card will be erased completely before the restored image is usable."
        )
        warning.setWordWrap(True)
        warning.setObjectName("SectionLead")

        self.body_layout().addWidget(card)
        self.body_layout().addWidget(warning)
        self.body_layout().addStretch(1)
        self.body_layout().addWidget(self._start, 0, QtCore.Qt.AlignLeft)

    def _on_start(self) -> None:
        source = self._image_picker.text()
        device = self._device_picker.current_device()
        if not source:
            QtWidgets.QMessageBox.warning(self, "Restore", "Choose a raw source image first.")
            return
        if device is None:
            QtWidgets.QMessageBox.warning(self, "Restore", "Select a removable target device.")
            return

        details = [
            f"Source: {source}",
            f"Target: {_device_label(device)}",
            "All data on the target card will be overwritten.",
        ]
        dialog = QtWidgets.QMessageBox(self)
        dialog.setIcon(QtWidgets.QMessageBox.Warning)
        dialog.setWindowTitle("Confirm Restore Destination")
        dialog.setText("This restore operation will erase the selected target device.")
        dialog.setInformativeText("Confirm the destination before continuing.")
        dialog.setDetailedText("\n".join(details))
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        if dialog.exec() != QtWidgets.QMessageBox.Yes:
            return

        total_bytes = Path(source).stat().st_size if Path(source).exists() else None
        self.run_requested.emit(
            {
                "title": "Restore Image",
                "total_bytes": total_bytes,
                "cli_args": ["restore", source, str(device.path)],
                "details": "\n".join(details),
            }
        )
