from __future__ import annotations

import inspect
from typing import get_type_hints, get_origin, get_args, Literal
from pydantic.fields import FieldInfo

from PySide6 import QtWidgets, QtCore

from pyobs.robotic.scheduler.targets.picker import Picker, CsvPicker

# All known Picker subclasses
_PICKER_CLASSES: dict[str, type[Picker]] = {
    "CsvPicker": CsvPicker,
}


def _picker_type_name(picker: Picker) -> str:
    return type(picker).__name__


class EditPickerWidget(QtWidgets.QGroupBox):
    picker_changed = QtCore.Signal(object)  # emits a Picker instance

    def __init__(self):
        super().__init__("Picker")

        self._picker: Picker | None = None
        self._updating = False
        self._field_widgets: dict[str, QtWidgets.QWidget] = {}

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
            self._type_changed(self._type_combo.currentText())
        else:
            name = _picker_type_name(picker)
            if name in _PICKER_CLASSES:
                self._type_combo.setCurrentText(name)
                self._rebuild_fields(type(picker))
                self._populate_fields(picker)

        self._updating = False

    def _clear_fields(self):
        for i in reversed(range(1, self._layout.rowCount())):
            self._layout.removeRow(i)
        self._field_widgets.clear()

    def _rebuild_fields(self, cls: type[Picker]):
        self._clear_fields()
        for field_name, field_info in cls.model_fields.items():
            if field_name == "class":
                continue
            widget = self._make_widget(field_name, field_info)
            if widget is not None:
                self._field_widgets[field_name] = widget
                self._layout.addRow(field_name.replace("_", " ").title(), widget)

    def _populate_fields(self, picker: Picker):
        for field_name, widget in self._field_widgets.items():
            value = getattr(picker, field_name)
            self._set_widget_value(widget, value)

    def _make_widget(self, field_name: str, field_info: FieldInfo) -> QtWidgets.QWidget | None:
        annotation = field_info.annotation

        # Literal -> combobox
        if get_origin(annotation) is Literal:
            combo = QtWidgets.QComboBox()
            combo.addItems([str(a) for a in get_args(annotation)])
            combo.currentTextChanged.connect(self._field_changed)
            return combo

        # str -> line edit
        if annotation is str:
            edit = QtWidgets.QLineEdit()
            if field_info.default is not None and field_info.default is not ...:
                edit.setPlaceholderText(str(field_info.default))
            edit.textChanged.connect(self._field_changed)
            return edit

        # int -> spinbox
        if annotation is int:
            spin = QtWidgets.QSpinBox()
            spin.setMinimum(-999999)
            spin.setMaximum(999999)
            spin.valueChanged.connect(self._field_changed)
            return spin

        # float -> double spinbox
        if annotation is float:
            spin = QtWidgets.QDoubleSpinBox()
            spin.setMinimum(-999999.0)
            spin.setMaximum(999999.0)
            spin.valueChanged.connect(self._field_changed)
            return spin

        # bool -> checkbox
        if annotation is bool:
            check = QtWidgets.QCheckBox()
            check.checkStateChanged.connect(self._field_changed)
            return check

        return None  # unsupported type — skip

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
        cls = _PICKER_CLASSES.get(type_name)
        if cls is None:
            return
        self._rebuild_fields(cls)
        # Construct a new picker with defaults
        if not self._updating:
            try:
                self._picker = cls()
                self._populate_fields(self._picker)
                self.picker_changed.emit(self._picker)
            except Exception:
                pass  # not all fields have defaults; user must fill them in

    @QtCore.Slot()
    def _field_changed(self):
        if self._updating or self._picker is None:
            return
        values = {name: self._get_widget_value(w) for name, w in self._field_widgets.items()}
        try:
            self._picker = type(self._picker)(**values)
            self.picker_changed.emit(self._picker)
        except Exception:
            pass  # validation error mid-edit — ignore until fields are complete
