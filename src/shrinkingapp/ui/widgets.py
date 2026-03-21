from __future__ import annotations

import math
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from shrinkingapp.models import (
    CompressionKind,
    EndpointCapability,
    EndpointKind,
    StorageEndpoint,
)
from shrinkingapp.system.endpoints import discover_endpoints


def human_bytes(value: int) -> str:
    if value <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = min(int(math.log(value, 1024)), len(units) - 1)
    scaled = value / (1024 ** index)
    if index == 0:
        return f"{int(scaled)} {units[index]}"
    return f"{scaled:.1f} {units[index]}"


def _endpoint_label(endpoint: StorageEndpoint) -> str:
    return endpoint.label


def _normalized_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def _same_path(left: str | Path, right: str | Path) -> bool:
    return _normalized_path(left) == _normalized_path(right)


class DevicePicker(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        required_capabilities: tuple[EndpointCapability, ...],
        placeholder: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._required_capabilities = required_capabilities
        self._placeholder = placeholder
        self._combo = QtWidgets.QComboBox()
        self._combo.setMinimumWidth(420)
        self._choose_button = QtWidgets.QPushButton("Choose")
        self._choose_button.setObjectName("SecondaryButton")
        self._choose_button.clicked.connect(self._combo.showPopup)
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.clicked.connect(self.refresh_devices)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._combo, 1)
        layout.addWidget(self._choose_button)
        layout.addWidget(self._refresh_button)

        self.refresh_devices()

    def refresh_devices(self) -> None:
        current_path = self.current_device_path()
        endpoints = discover_endpoints(
            required_capabilities=self._required_capabilities,
            allowed_kinds=(EndpointKind.BLOCK_DEVICE,),
        )
        self._combo.clear()
        placeholder = self._placeholder
        if endpoints:
            placeholder = f"{self._placeholder} ({len(endpoints)} found)"
        self._combo.addItem(placeholder, None)
        for endpoint in endpoints:
            self._combo.addItem(_endpoint_label(endpoint), endpoint)

        if current_path is not None:
            for index in range(self._combo.count()):
                endpoint = self._combo.itemData(index)
                if endpoint is not None and endpoint.path == current_path:
                    self._combo.setCurrentIndex(index)
                    break

    def current_device(self) -> StorageEndpoint | None:
        return self._combo.currentData()

    def current_device_path(self) -> Path | None:
        endpoint = self.current_device()
        return None if endpoint is None else endpoint.path

    def set_enabled(self, enabled: bool) -> None:
        self._combo.setEnabled(enabled)
        self._choose_button.setEnabled(enabled)
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


class LocationEndpointPicker(QtWidgets.QWidget):
    location_selected = QtCore.Signal(str)

    def __init__(
        self,
        *,
        required_capabilities: tuple[EndpointCapability, ...],
        placeholder: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._required_capabilities = required_capabilities
        self._placeholder = placeholder
        self._combo = QtWidgets.QComboBox()
        self._combo.setMinimumWidth(420)
        self._choose_button = QtWidgets.QPushButton("Choose")
        self._choose_button.setObjectName("SecondaryButton")
        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.setObjectName("SecondaryButton")

        self._choose_button.clicked.connect(self._combo.showPopup)
        self._combo.currentIndexChanged.connect(self._emit_selection)
        self._refresh_button.clicked.connect(self.refresh_locations)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._combo, 1)
        layout.addWidget(self._choose_button)
        layout.addWidget(self._refresh_button)

        self.refresh_locations()

    def refresh_locations(self) -> None:
        current_path = self.current_path()
        endpoints = discover_endpoints(
            required_capabilities=self._required_capabilities,
            allowed_kinds=(EndpointKind.FILESYSTEM,),
        )
        self._combo.clear()
        placeholder = self._placeholder
        if endpoints:
            placeholder = f"{self._placeholder} ({len(endpoints)} found)"
        self._combo.addItem(placeholder, None)
        for endpoint in endpoints:
            self._combo.addItem(f"{endpoint.label}  |  {endpoint.path}", str(endpoint.path))

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
        self._choose_button.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)

    def _emit_selection(self, *_args: object) -> None:
        path = self.current_path()
        if path:
            self.location_selected.emit(path)


class OperationConfirmationDialog(QtWidgets.QDialog):
    def __init__(
        self,
        *,
        title: str,
        heading: str,
        message: str,
        rows: list[tuple[str, str]],
        warning: str | None = None,
        confirm_label: str = "Confirm",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(660, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        heading_label = QtWidgets.QLabel(heading)
        heading_label.setObjectName("SectionTitle")
        heading_label.setWordWrap(True)
        message_label = QtWidgets.QLabel(message)
        message_label.setObjectName("SectionLead")
        message_label.setWordWrap(True)
        layout.addWidget(heading_label)
        layout.addWidget(message_label)

        if warning:
            warning_frame = QtWidgets.QFrame()
            warning_frame.setObjectName("SectionCard")
            warning_layout = QtWidgets.QVBoxLayout(warning_frame)
            warning_layout.setContentsMargins(14, 12, 14, 12)
            warning_text = QtWidgets.QLabel(warning)
            warning_text.setWordWrap(True)
            warning_text.setObjectName("SectionLead")
            warning_layout.addWidget(warning_text)
            layout.addWidget(warning_frame)

        summary = QtWidgets.QGroupBox("Selection Summary")
        summary_layout = QtWidgets.QFormLayout(summary)
        summary_layout.setContentsMargins(14, 14, 14, 14)
        for label, value in rows:
            value_label = QtWidgets.QLabel(value)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            summary_layout.addRow(label, value_label)
        layout.addWidget(summary)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        confirm_button = buttons.addButton(confirm_label, QtWidgets.QDialogButtonBox.AcceptRole)
        confirm_button.setObjectName("DangerButton" if "overwrite" in (warning or "").lower() else "PrimaryButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


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
            "Create a working image from either a removable device or an existing image file and save it to a writable location.",
            parent,
        )
        self._source_mode = QtWidgets.QComboBox()
        self._source_mode.addItem("Removable Device", "device")
        self._source_mode.addItem("Image File", "image")
        self._source_mode.currentIndexChanged.connect(self._sync_source_mode)
        self._device_picker = DevicePicker(
            required_capabilities=(EndpointCapability.READABLE, EndpointCapability.REMOVABLE),
            placeholder="Select a removable source device",
        )
        self._source_locations = LocationEndpointPicker(
            required_capabilities=(EndpointCapability.READABLE, EndpointCapability.BROWSABLE),
            placeholder="Select a readable source location",
        )
        self._source_locations.location_selected.connect(self._apply_source_location)
        self._source_file_picker = FilePicker(
            mode="open",
            caption="Choose Source Image",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._source_stack = QtWidgets.QStackedWidget()
        device_source = QtWidgets.QWidget()
        device_layout = QtWidgets.QVBoxLayout(device_source)
        device_layout.setContentsMargins(0, 0, 0, 0)
        device_layout.setSpacing(10)
        device_layout.addWidget(self._device_picker)
        image_source = QtWidgets.QWidget()
        image_layout = QtWidgets.QFormLayout(image_source)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(10)
        image_layout.addRow("Source Location", self._source_locations)
        image_layout.addRow("Source Image", self._source_file_picker)
        self._source_stack.addWidget(device_source)
        self._source_stack.addWidget(image_source)
        self._source_note = QtWidgets.QLabel(
            "Use Removable Device for direct SD-card capture. Use Image File when the source image already lives on the SSD or another readable location."
        )
        self._source_note.setObjectName("SectionLead")
        self._source_note.setWordWrap(True)
        self._output_picker = FilePicker(
            mode="save",
            caption="Choose Capture Destination",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._destination_shortcuts = LocationEndpointPicker(
            required_capabilities=(EndpointCapability.WRITABLE, EndpointCapability.BROWSABLE),
            placeholder="Select a writable destination location",
        )
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
        form.addRow("Source Type", self._source_mode)
        form.addRow("Capture Source", self._source_stack)
        form.addRow("", self._source_note)
        form.addRow("Save In Location", self._destination_shortcuts)
        form.addRow("Output Image File", self._output_picker)
        form.addRow("Compression", self._compression)
        form.addRow("", self._parallel)

        self.body_layout().addWidget(card)
        self.body_layout().addStretch(1)
        self.body_layout().addWidget(self._start, 0, QtCore.Qt.AlignLeft)
        self._sync_source_mode()

    def _apply_destination_location(self, path: str) -> None:
        self._output_picker.set_directory(path, suggested_filename="pi-source.img")

    def _apply_source_location(self, path: str) -> None:
        self._source_file_picker.set_directory(path)

    def _sync_source_mode(self) -> None:
        mode = self._source_mode.currentData()
        self._source_stack.setCurrentIndex(0 if mode == "device" else 1)

    def _on_start(self) -> None:
        output_path = self._output_picker.text()
        if not output_path:
            QtWidgets.QMessageBox.warning(self, "Capture", "Choose a destination image path.")
            return

        mode = self._source_mode.currentData()
        source_label: str
        source_path: Path
        total_bytes: int | None

        if mode == "device":
            device = self._device_picker.current_device()
            if device is None:
                QtWidgets.QMessageBox.warning(self, "Capture", "Select a removable source device first.")
                return
            source_label = _endpoint_label(device)
            source_path = device.path
            total_bytes = device.size_bytes
        else:
            source_text = self._source_file_picker.text()
            if not source_text:
                QtWidgets.QMessageBox.warning(self, "Capture", "Choose a source image file first.")
                return
            source_path = Path(source_text).expanduser()
            if not source_path.exists() or not source_path.is_file():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Capture",
                    "Choose an existing source image file. If you selected only a source location, use Browse to pick the image inside it.",
                )
                return
            source_label = str(source_path)
            total_bytes = source_path.stat().st_size

        output_file = Path(output_path).expanduser()
        if _same_path(source_path, output_file):
            QtWidgets.QMessageBox.warning(
                self,
                "Capture",
                "The source and destination paths are the same. Choose a different output image path.",
            )
            return
        compression = self._compression.currentData()
        dialog = OperationConfirmationDialog(
            title="Confirm Capture",
            heading="Start the capture job with the selected source and destination?",
            message="Verify the selected source endpoint and destination image carefully before continuing.",
            warning="Writing to the wrong destination file path can overwrite an existing image.",
            rows=[
                ("Source type", "Removable Device" if mode == "device" else "Image File"),
                ("Source", source_label),
                ("Destination folder", str(output_file.parent)),
                ("Destination image", str(output_file)),
                ("Compression", compression or "None"),
                ("Expected source size", human_bytes(total_bytes or 0)),
            ],
            confirm_label="Start Capture",
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        details = [
            f"Source type: {'Removable Device' if mode == 'device' else 'Image File'}",
            f"Source: {source_label}",
            f"Destination: {output_file}",
            f"Compression: {compression or 'None'}",
        ]
        self.run_requested.emit(
            {
                "title": "Capture Image",
                "total_bytes": total_bytes,
                "cli_args": [
                    "capture",
                    str(source_path),
                    str(output_file),
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
            "Open an image from any readable location, shrink it, and optionally compress it. Leaving the destination blank modifies the image in place.",
            parent,
        )
        self._image_picker = FilePicker(
            mode="open",
            caption="Choose Source Image",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._source_locations = LocationEndpointPicker(
            required_capabilities=(EndpointCapability.READABLE, EndpointCapability.BROWSABLE),
            placeholder="Select a readable source location",
        )
        self._source_locations.location_selected.connect(self._apply_source_location)
        self._output_picker = FilePicker(
            mode="save",
            caption="Choose Shrunk Image Destination",
            file_filter="Disk Images (*.img *.img.gz *.img.xz);;All Files (*)",
        )
        self._destination_shortcuts = LocationEndpointPicker(
            required_capabilities=(EndpointCapability.WRITABLE, EndpointCapability.BROWSABLE),
            placeholder="Select a writable destination location",
        )
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
        form.addRow("Source Location", self._source_locations)
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

    def _apply_source_location(self, path: str) -> None:
        self._image_picker.set_directory(path)

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

        source_path = Path(source).expanduser()
        if not source_path.exists() or not source_path.is_file():
            QtWidgets.QMessageBox.warning(
                self,
                "Shrink",
                "Choose an existing image file. If you selected only a source location, use Browse to pick the image inside it.",
            )
            return

        output = self._output_picker.text()
        if output and _same_path(source, output):
            QtWidgets.QMessageBox.warning(
                self,
                "Shrink",
                "The source and destination image paths are the same. Leave the destination blank for an in-place shrink or choose a different output file.",
            )
            return

        compression = self._compression.currentData()
        source_size = source_path.stat().st_size

        destination_text = output or "In place"
        warning = None
        if not output:
            warning = "The selected image file will be modified in place."

        dialog = OperationConfirmationDialog(
            title="Confirm Shrink",
            heading="Start the shrink job with the selected destination?",
            message="Verify the source image and destination before continuing.",
            warning=warning,
            rows=[
                ("Source image", str(source_path)),
                ("Destination", destination_text),
                ("Compression", compression or "None"),
                ("Source size", human_bytes(source_size)),
            ],
            confirm_label="Start Shrink",
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        cli_args = ["shrink", str(source_path)]
        destination_value = output or "In place"
        details = [
            f"Source: {source_path}",
            f"Destination: {destination_value}",
            f"Compression: {compression or 'None'}",
        ]
        if output:
            cli_args.extend(["--output", str(Path(output).expanduser())])
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
            "Open a raw image from any readable location and write it to a removable target device. The destination confirmation is destructive and required.",
            parent,
        )
        self._image_picker = FilePicker(
            mode="open",
            caption="Choose Image To Restore",
            file_filter="Disk Images (*.img);;All Files (*)",
        )
        self._source_locations = LocationEndpointPicker(
            required_capabilities=(EndpointCapability.READABLE, EndpointCapability.BROWSABLE),
            placeholder="Select a readable source location",
        )
        self._source_locations.location_selected.connect(self._apply_source_location)
        self._device_picker = DevicePicker(
            required_capabilities=(EndpointCapability.WRITABLE, EndpointCapability.REMOVABLE),
            placeholder="Select a removable target device",
        )
        self._start = QtWidgets.QPushButton("Start Restore")
        self._start.setObjectName("DangerButton")
        self._start.clicked.connect(self._on_start)

        card = QtWidgets.QGroupBox("Restore Target")
        form = QtWidgets.QFormLayout(card)
        form.addRow("Source Location", self._source_locations)
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

    def _apply_source_location(self, path: str) -> None:
        self._image_picker.set_directory(path)

    def _on_start(self) -> None:
        source = self._image_picker.text()
        device = self._device_picker.current_device()
        if not source:
            QtWidgets.QMessageBox.warning(self, "Restore", "Choose a raw source image first.")
            return
        source_path = Path(source).expanduser()
        if not source_path.exists() or not source_path.is_file():
            QtWidgets.QMessageBox.warning(
                self,
                "Restore",
                "Choose an existing image file. If you selected only a source location, use Browse to pick the image inside it.",
            )
            return
        if device is None:
            QtWidgets.QMessageBox.warning(self, "Restore", "Select a removable target device.")
            return

        dialog = OperationConfirmationDialog(
            title="Confirm Restore",
            heading="This restore operation will erase the selected target device.",
            message="Verify both the source image and the target card before continuing.",
            warning="All data on the target card will be overwritten.",
            rows=[
                ("Source image", str(source_path)),
                ("Target device", _endpoint_label(device)),
                ("Target capacity", human_bytes(device.size_bytes or 0)),
            ],
            confirm_label="Erase And Restore",
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        details = [
            f"Source: {source_path}",
            f"Target: {_endpoint_label(device)}",
            "All data on the target card will be overwritten.",
        ]
        total_bytes = source_path.stat().st_size
        self.run_requested.emit(
            {
                "title": "Restore Image",
                "total_bytes": total_bytes,
                "cli_args": ["restore", str(source_path), str(device.path)],
                "details": "\n".join(details),
            }
        )
