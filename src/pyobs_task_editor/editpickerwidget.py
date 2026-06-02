from __future__ import annotations

from typing import Any, get_origin, get_args, Literal
from pydantic.fields import FieldInfo

import yaml
from PySide6 import QtWidgets, QtCore

from pyobs.robotic.scheduler.targets.picker import Picker, CsvPicker


class CustomPicker(Picker):
    """Local-only picker that holds arbitrary YAML, passed through as-is on serialization."""

    raw: dict[str, Any] = {}

    async def __call__(self, *args, **kwargs):
        raise NotImplementedError("CustomPicker is a local-only type and cannot be called.")

    def model_dump(self, **kwargs) -> dict[str, Any]:
        return dict(self.raw)


# All known Picker subclasses — add new ones here as pyobs-core grows
_PICKER_CLASSES: dict[str, type] = {
    "CsvPicker": CsvPicker,
    "Custom": CustomPicker,
}

_CUSTOM = "Custom"


def _picker_type_name(picker: Picker) -> str:
    if isinstance(picker, CustomPicker):
        return _CUSTOM
    return type(picker).__name__


class EditPickerWidget(QtWidgets.QGroupBox):
    picker_changed = QtCore.Signal(object)  # emits a Picker instance

    def __init__(self):
        super().__init__("Picker")

        self._picker: Picker | None = None
        self._updating = False
        self._field_widgets: dict[str, QtWidgets.QWidget] = {}
        self._yaml_widget: QtWidgets.QPlainTextEdit | None = None
        self._yaml_status: QtWidgets.QLabel | None = None

        self._layout = QtWidgets.QFormLayout()
        self.setLayout(self._layout)

        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.addItems(list(_PICKER_CLASSES.keys()))
        self._type_combo.currentTextChanged.connect(self._type_changed)
        self._layout.addRow("Type", self._type_combo)

    def set_picker(self, picker: Picker | None):
        self._updating = True
        self._picker = picker

        if picker is None:
            self._type_combo.setCurrentIndex(0)
            self._rebuild_fields(self._type_combo.currentText())
        else:
            name = _picker_type_name(picker)
            self._type_combo.setCurrentText(name)
            self._rebuild_fields(name)
            if isinstance(picker, CustomPicker):
                self._yaml_widget.setPlainText(yaml.dump(picker.raw, default_flow_style=False))
            else:
                self._populate_fields(picker)

        self._updating = False

    def _clear_fields(self):
        for i in reversed(range(1, self._layout.rowCount())):
            self._layout.removeRow(i)
        self._field_widgets.clear()
        self._yaml_widget = None
        self._yaml_status = None

    def _rebuild_fields(self, type_name: str):
        self._clear_fields()

        if type_name == _CUSTOM:
            self._yaml_widget = QtWidgets.QPlainTextEdit()
            self._yaml_widget.setPlaceholderText("Enter picker YAML here...")
            self._yaml_widget.textChanged.connect(self._yaml_changed)
            self._layout.addRow(self._yaml_widget)
            self._yaml_status = QtWidgets.QLabel()
            self._layout.addRow(self._yaml_status)
        else:
            cls = _PICKER_CLASSES.get(type_name)
            if cls is None:
                return
            for field_name, field_info in cls.model_fields.items():
                if field_name == "class":
                    continue
                widget = self._make_widget(field_name, field_info)
                if widget is not None:
                    self._field_widgets[field_name] = widget
                    self._layout.addRow(field_name.replace("_", " ").title(), widget)

    def _populate_fields(self, picker: Picker):
        for field_name, widget in self._field_widgets.items():
            self._set_widget_value(widget, getattr(picker, field_name))

    def _make_widget(self, field_name: str, field_info: FieldInfo) -> QtWidgets.QWidget | None:
        annotation = field_info.annotation

        if get_origin(annotation) is Literal:
            combo = QtWidgets.QComboBox()
            combo.addItems([str(a) for a in get_args(annotation)])
            combo.currentTextChanged.connect(self._field_changed)
            return combo
        if annotation is str:
            edit = QtWidgets.QLineEdit()
            if field_info.default is not None and field_info.default is not ...:
                edit.setPlaceholderText(str(field_info.default))
            edit.textChanged.connect(self._field_changed)
            return edit
        if annotation is int:
            spin = QtWidgets.QSpinBox()
            spin.setMinimum(-999999)
            spin.setMaximum(999999)
            spin.valueChanged.connect(self._field_changed)
            return spin
        if annotation is float:
            spin = QtWidgets.QDoubleSpinBox()
            spin.setMinimum(-999999.0)
            spin.setMaximum(999999.0)
            spin.valueChanged.connect(self._field_changed)
            return spin
        if annotation is bool:
            check = QtWidgets.QCheckBox()
            check.checkStateChanged.connect(self._field_changed)
            return check

        return None

    def _set_widget_value(self, widget: QtWidgets.QWidget, value):
        if isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentText(str(value))
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(str(value) if value is not None else "")
        elif isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            widget.setValue(value)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(value))

    def _get_widget_value(self, widget: QtWidgets.QWidget):
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        elif isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        elif isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()

    @QtCore.Slot(str)
    def _type_changed(self, type_name: str):
        self._rebuild_fields(type_name)

        if not self._updating:
            if type_name == _CUSTOM:
                # Start with an empty custom picker
                self._picker = CustomPicker(raw={})
                self.picker_changed.emit(self._picker)
            else:
                cls = _PICKER_CLASSES.get(type_name)
                if cls is None:
                    return
                if isinstance(self._picker, cls):
                    self._populate_fields(self._picker)
                    self.picker_changed.emit(self._picker)
                else:
                    try:
                        self._picker = cls()
                        self._populate_fields(self._picker)
                        self.picker_changed.emit(self._picker)
                    except Exception:
                        self._picker = None  # required fields missing; wait for user input

    @QtCore.Slot()
    def _yaml_changed(self):
        if self._updating or self._yaml_widget is None:
            return
        try:
            raw = yaml.safe_load(self._yaml_widget.toPlainText()) or {}
        except yaml.YAMLError as e:
            self.set_error(f"Invalid YAML: {e}")
            return
        try:
            # Validate the raw dict as a Picker to catch schema errors immediately
            Picker.model_validate(raw)
            self.set_error(None)
        except Exception as e:
            self.set_error(str(e))
        # Always update the picker regardless — CustomPicker stores raw YAML as-is
        self._picker = CustomPicker(raw=raw)
        self.picker_changed.emit(self._picker)

    def set_error(self, message: str | None):
        """Called externally to report a validation error on the current picker value."""
        if self._yaml_status is None:
            return
        if message is None:
            self._yaml_status.setText("✓ Valid")
            self._yaml_status.setStyleSheet("color: green;")
        else:
            self._yaml_status.setText(f"✗ {message}")
            self._yaml_status.setStyleSheet("color: red;")

    @QtCore.Slot()
    def _field_changed(self):
        if self._updating:
            return
        type_name = self._type_combo.currentText()
        cls = _PICKER_CLASSES.get(type_name)
        if cls is None:
            return
        values = {name: self._get_widget_value(w) for name, w in self._field_widgets.items()}
        try:
            self._picker = cls(**values)
            self.picker_changed.emit(self._picker)
        except Exception:
            pass
