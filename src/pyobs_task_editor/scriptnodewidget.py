from __future__ import annotations
import enum
import inspect
import types
import yaml
from typing import Any, get_origin, get_args, Literal, Union

from pydantic import BaseModel
from PySide6 import QtWidgets, QtCore
import qtawesome as qa

from pyobs.robotic.task import Script
import pyobs.robotic.scripts as scripts_module

IGNORED_FIELDS = {"exptime_done", "class"}


def _get_script_classes() -> dict[str, type]:
    return {
        name: obj
        for name, obj in inspect.getmembers(scripts_module)
        if inspect.isclass(obj) and issubclass(obj, Script) and name != "Script"
    }


def _is_optional(annotation) -> tuple[bool, Any]:
    """Returns (is_optional, inner_type). Unwraps X | None."""
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return True, args[0]
    return False, annotation


def _script_list_fields(cls: type) -> list[str]:
    """Return names of fields that are Script, Script | None, or list[Script]."""
    result = []
    for field_name, field_info in cls.model_fields.items():
        _, inner = _is_optional(field_info.annotation)
        origin = get_origin(inner)
        args = get_args(inner)
        if origin is list and len(args) == 1 and inspect.isclass(args[0]) and issubclass(args[0], Script):
            result.append(field_name)
        elif inspect.isclass(inner) and issubclass(inner, Script):
            result.append(field_name)
    return result


def _is_container(cls: type) -> bool:
    return len(_script_list_fields(cls)) > 0


def _make_widget(annotation, value, on_change, optional: bool = False) -> QtWidgets.QWidget | None:
    """Recursively build a widget for any annotation type."""

    is_opt, inner = _is_optional(annotation)
    if is_opt:
        return _make_widget(inner, value, on_change, optional=True)

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Literal → combobox
    if origin is Literal:
        w = QtWidgets.QComboBox()
        w.addItems([str(a) for a in args])
        if value is not None:
            w.setCurrentText(str(value))
        w.currentTextChanged.connect(on_change)
        return w

    # Enum → combobox
    if inspect.isclass(annotation) and issubclass(annotation, enum.Enum):
        w = QtWidgets.QComboBox()
        w.addItems([e.value for e in annotation])
        if value is not None:
            w.setCurrentText(str(value) if isinstance(value, str) else value.value)
        w.currentTextChanged.connect(on_change)
        return w

    # bool → checkbox
    if annotation is bool:
        w = QtWidgets.QCheckBox()
        w.setChecked(bool(value) if value is not None else False)
        w.checkStateChanged.connect(on_change)
        return w

    # int → spinbox
    if annotation is int:
        w = QtWidgets.QSpinBox()
        w.setMinimum(-999999)
        w.setMaximum(999999)
        if value is not None:
            w.setValue(int(value))
        w.valueChanged.connect(on_change)
        return w

    # float → double spinbox
    if annotation is float:
        w = QtWidgets.QDoubleSpinBox()
        w.setMinimum(-999999.0)
        w.setMaximum(999999.0)
        if value is not None:
            w.setValue(float(value))
        w.valueChanged.connect(on_change)
        return w

    # str → line edit (empty string = None when optional)
    if annotation is str:
        w = QtWidgets.QLineEdit()
        if optional:
            w.setPlaceholderText("(none)")
        w.setText(str(value) if value is not None else "")
        w.textChanged.connect(on_change)
        return w

    # tuple[X, X, ...] → row of spinboxes
    if origin is tuple and all(a in (int, float) for a in args):
        container = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        container.setLayout(row)
        values = list(value) if value is not None else [0] * len(args)
        for i, a in enumerate(args):
            if a is int:
                sb = QtWidgets.QSpinBox()
                sb.setMinimum(-999999)
                sb.setMaximum(999999)
                sb.setValue(int(values[i]) if i < len(values) else 0)
            else:
                sb = QtWidgets.QDoubleSpinBox()
                sb.setMinimum(-999999.0)
                sb.setMaximum(999999.0)
                sb.setValue(float(values[i]) if i < len(values) else 0.0)
            sb.valueChanged.connect(on_change)
            row.addWidget(sb)
        container._spinboxes = [row.itemAt(i).widget() for i in range(row.count())]
        return container

    # Script subclass → nested ScriptNodeWidget
    if inspect.isclass(annotation) and issubclass(annotation, Script):
        return ScriptNodeWidget(value or {}, depth=0, on_change=on_change)

    # list[Script subclass] → handled as children in ScriptNodeWidget, not here
    # list[BaseModel] → vertical list with add/remove
    if origin is list and len(args) == 1 and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
        return _ListOfModelsWidget(args[0], value or [], on_change)

    # BaseModel → nested group with form
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return _NestedModelWidget(annotation, value or {}, on_change)

    # list[primitives or union of primitives] → list with add/remove
    if origin is list and len(args) == 1:
        origin_item = get_origin(args[0])
        if origin_item is Union or origin_item is types.UnionType:
            return _ListOfPrimitivesWidget(str, value or [], on_change)
        elif args[0] in (str, int, float):
            return _ListOfPrimitivesWidget(args[0], value or [], on_change)

    # list[primitives] → vertical list with add/remove
    if origin is list and len(args) == 1 and args[0] in (str, int, float):
        return _ListOfPrimitivesWidget(args[0], value or [], on_change)

    # dict → YAML text area
    if annotation is dict or origin is dict:
        w = QtWidgets.QPlainTextEdit()
        w.setMaximumHeight(100)
        w.setPlaceholderText("YAML...")
        w.setPlainText(yaml.dump(value, default_flow_style=False) if value else "")
        w.textChanged.connect(on_change)
        return w

    return None  # unsupported


def _get_widget_value(widget: QtWidgets.QWidget, annotation, optional: bool = False) -> Any:
    """Extract the current value from a widget, matching the field annotation."""

    is_opt, inner = _is_optional(annotation)
    if is_opt:
        return _get_widget_value(widget, inner, optional=True)

    if isinstance(widget, QtWidgets.QComboBox):
        return widget.currentText()
    if isinstance(widget, QtWidgets.QCheckBox):
        return widget.isChecked()
    if isinstance(widget, QtWidgets.QSpinBox):
        return widget.value()
    if isinstance(widget, QtWidgets.QDoubleSpinBox):
        return widget.value()
    if isinstance(widget, QtWidgets.QLineEdit):
        v = widget.text().strip()
        return v if v else None
    if hasattr(widget, "_spinboxes"):
        return [sb.value() for sb in widget._spinboxes]
    if isinstance(widget, ScriptNodeWidget):
        return widget.get_data()
    if isinstance(widget, (_ListOfModelsWidget, _NestedModelWidget)):
        return widget.get_data()
    if isinstance(widget, QtWidgets.QPlainTextEdit):
        try:
            return yaml.safe_load(widget.toPlainText()) or {}
        except yaml.YAMLError:
            return {}
    if isinstance(widget, _ListOfPrimitivesWidget):
        return widget.get_data()
    return None


class _NestedModelWidget(QtWidgets.QGroupBox):
    """Dynamically builds a form for any pydantic BaseModel."""

    changed = QtCore.Signal()

    def __init__(self, cls: type[BaseModel], data: dict, on_change):
        super().__init__(cls.__name__)
        self._cls = cls
        self._data = data
        self._field_widgets: dict[str, QtWidgets.QWidget] = {}

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        for field_name, field_info in cls.model_fields.items():
            if field_name in IGNORED_FIELDS:
                continue
            value = data.get(field_name)
            widget = _make_widget(field_info.annotation, value, on_change)
            if widget is not None:
                self._field_widgets[field_name] = widget
                layout.addRow(field_name.replace("_", " ").title(), widget)

        self.changed.connect(on_change)

    def get_data(self) -> dict:
        return {
            name: _get_widget_value(w, self._cls.model_fields[name].annotation)
            for name, w in self._field_widgets.items()
        }


class _ListOfPrimitivesWidget(QtWidgets.QWidget):
    def __init__(self, item_type: type, data: list, on_change):
        super().__init__()
        self._item_type = item_type
        self._on_change = on_change
        self._item_widgets: list[QtWidgets.QWidget] = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        for value in data:
            self._add_item(value)

        add_btn = QtWidgets.QToolButton()
        add_btn.setIcon(qa.icon("fa5s.plus"))
        add_btn.setText("Add")
        add_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        add_btn.clicked.connect(lambda: self._add_item_default())
        self._layout.addWidget(add_btn)

    def _make_item_widget(self, value=None) -> QtWidgets.QWidget:
        if self._item_type is int:
            w = QtWidgets.QSpinBox()
            w.setMinimum(-999999)
            w.setMaximum(999999)
            if value is not None:
                w.setValue(int(value))
            w.valueChanged.connect(self._on_change)
        elif self._item_type is float:
            w = QtWidgets.QDoubleSpinBox()
            w.setMinimum(-999999.0)
            w.setMaximum(999999.0)
            if value is not None:
                w.setValue(float(value))
            w.valueChanged.connect(self._on_change)
        else:
            w = QtWidgets.QLineEdit()
            w.setText(str(value) if value is not None else "")
            w.textChanged.connect(self._on_change)
        return w

    def _add_item(self, value=None):
        item_widget = self._make_item_widget(value)

        wrapper = QtWidgets.QWidget()
        wrapper_layout = QtWidgets.QHBoxLayout()
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper.setLayout(wrapper_layout)
        wrapper_layout.addWidget(item_widget, stretch=1)

        remove_btn = QtWidgets.QToolButton()
        remove_btn.setIcon(qa.icon("fa5s.minus"))
        remove_btn.clicked.connect(lambda: self._remove_item(wrapper, item_widget))
        wrapper_layout.addWidget(remove_btn)

        self._layout.insertWidget(self._layout.count() - 1, wrapper)
        self._item_widgets.append(item_widget)

    def _add_item_default(self):
        self._add_item()
        self._on_change()

    def _remove_item(self, wrapper: QtWidgets.QWidget, item_widget: QtWidgets.QWidget):
        self._item_widgets.remove(item_widget)
        wrapper.deleteLater()
        self._on_change()

    def get_data(self) -> list:
        result = []
        for w in self._item_widgets:
            if isinstance(w, QtWidgets.QSpinBox):
                result.append(w.value())
            elif isinstance(w, QtWidgets.QDoubleSpinBox):
                result.append(w.value())
            else:
                result.append(w.text())
        return result


class _ListOfModelsWidget(QtWidgets.QWidget):
    """Dynamically builds a vertical list of BaseModel forms with add/remove."""

    changed = QtCore.Signal()

    def __init__(self, item_cls: type[BaseModel], data: list[dict], on_change):
        super().__init__()
        self._item_cls = item_cls
        self._item_widgets: list[_NestedModelWidget] = []
        self._on_change = on_change

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        for item_data in data:
            self._add_item(item_data)

        add_btn = QtWidgets.QToolButton()
        add_btn.setIcon(qa.icon("fa5s.plus"))
        add_btn.setText(f"Add {item_cls.__name__}")
        add_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        add_btn.clicked.connect(self._add_item_default)
        self._layout.addWidget(add_btn)

    def _add_item(self, data: dict | None = None):
        if data is None:
            data = {}
        item_widget = _NestedModelWidget(self._item_cls, data, self._on_change)

        wrapper = QtWidgets.QWidget()
        wrapper_layout = QtWidgets.QHBoxLayout()
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper.setLayout(wrapper_layout)
        wrapper_layout.addWidget(item_widget, stretch=1)

        remove_btn = QtWidgets.QToolButton()
        remove_btn.setIcon(qa.icon("fa5s.minus"))
        remove_btn.clicked.connect(lambda: self._remove_item(wrapper, item_widget))
        wrapper_layout.addWidget(remove_btn, alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        self._layout.insertWidget(self._layout.count() - 1, wrapper)
        self._item_widgets.append(item_widget)

    @QtCore.Slot()
    def _add_item_default(self):
        self._add_item()
        self._on_change()

    def _remove_item(self, wrapper: QtWidgets.QWidget, item_widget: _NestedModelWidget):
        self._item_widgets.remove(item_widget)
        wrapper.deleteLater()
        self._on_change()

    def get_data(self) -> list[dict]:
        return [w.get_data() for w in self._item_widgets]


class ScriptNodeWidget(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self, data: dict[str, Any], depth: int = 0, on_change=None):
        super().__init__()
        self._data = data
        self._depth = depth
        self._child_widgets: list[tuple[str, ScriptNodeWidget]] = []  # (field_name, widget)
        self._field_widgets: dict[str, QtWidgets.QWidget] = {}

        if on_change is not None:
            self.changed.connect(on_change)

        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(depth * 16, 0, 0, 0)
        self.setLayout(outer)

        header = QtWidgets.QHBoxLayout()
        outer.addLayout(header)

        self._type_combo = QtWidgets.QComboBox()
        classes = _get_script_classes()
        self._type_combo.addItems(sorted(classes.keys()))
        current_type = data.get("class", "").rsplit(".", 1)[-1]
        if current_type in classes:
            self._type_combo.setCurrentText(current_type)
        self._type_combo.currentTextChanged.connect(self._type_changed)
        header.addWidget(self._type_combo)
        header.addStretch()

        self._form_group = QtWidgets.QGroupBox()
        self._form_group.setFlat(True)
        self._form_layout = QtWidgets.QFormLayout()
        self._form_layout.setContentsMargins(0, 0, 0, 0)
        self._form_group.setLayout(self._form_layout)
        outer.addWidget(self._form_group)

        self._children_group = QtWidgets.QWidget()
        self._children_layout = QtWidgets.QVBoxLayout()
        self._children_layout.setContentsMargins(0, 0, 0, 0)
        self._children_group.setLayout(self._children_layout)
        outer.addWidget(self._children_group)

        self._rebuild(data)

    def _rebuild(self, data: dict[str, Any]):
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)
        self._field_widgets.clear()
        self._child_widgets.clear()
        while self._children_layout.count():
            item = self._children_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        type_name = self._type_combo.currentText()
        classes = _get_script_classes()
        cls = classes.get(type_name)
        if cls is None:
            return

        script_fields = _script_list_fields(cls)
        is_container = _is_container(cls)
        self._children_group.setVisible(is_container)

        for field_name, field_info in cls.model_fields.items():
            if field_name in IGNORED_FIELDS:
                continue
            if field_name in script_fields:
                continue  # handled as children below

            value = data.get(field_name)
            widget = _make_widget(field_info.annotation, value, self._field_changed)
            if widget is not None:
                self._field_widgets[field_name] = widget
                self._form_layout.addRow(field_name.replace("_", " ").title(), widget)

        if is_container:
            for field_name in script_fields:
                field_info = cls.model_fields[field_name]
                _, inner = _is_optional(field_info.annotation)
                origin = get_origin(inner)

                # Section label if more than one script field
                if len(script_fields) > 1:
                    label = QtWidgets.QLabel(f"<b>{field_name.replace('_', ' ').title()}</b>")
                    self._children_layout.addWidget(label)

                if origin is list:
                    # list[Script] — multiple children with add button
                    for child_data in data.get(field_name) or []:
                        self._add_child(child_data, field_name)

                    add_btn = QtWidgets.QToolButton()
                    add_btn.setIcon(qa.icon("fa5s.plus"))
                    add_btn.setText(f"Add {field_name.replace('_', ' ')}")
                    add_btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                    add_btn.clicked.connect(lambda checked=False, fn=field_name: self._add_child_default(fn))
                    self._children_layout.addWidget(add_btn)
                else:
                    # Single Script (or Script | None) — always show one child
                    child_data = data.get(field_name) or {}
                    self._add_child(child_data, field_name)

    @QtCore.Slot()
    def _field_changed(self):
        type_name = self._type_combo.currentText()
        classes = _get_script_classes()
        cls = classes.get(type_name)
        if cls is None:
            return
        self._data = {"class": f"{cls.__module__}.{type_name}"}
        for field_name, widget in self._field_widgets.items():
            self._data[field_name] = _get_widget_value(widget, cls.model_fields[field_name].annotation)
        self._collect_children(cls)
        self.changed.emit()

    @QtCore.Slot(str)
    def _type_changed(self, type_name: str):
        from pydantic_core import PydanticUndefined

        classes = _get_script_classes()
        cls = classes.get(type_name)
        if cls is None:
            return
        self._data = {"class": f"{cls.__module__}.{type_name}"}
        for field_name, field_info in cls.model_fields.items():
            if (
                field_info.default is not None
                and field_info.default is not ...
                and field_info.default is not PydanticUndefined
            ):
                self._data[field_name] = field_info.default
            elif field_info.default_factory is not None:
                self._data[field_name] = field_info.default_factory()
        self._rebuild(self._data)
        self.changed.emit()

    def _add_child(self, child_data: dict | None = None, field_name: str = "scripts"):
        if child_data is None or child_data == {}:
            classes = _get_script_classes()
            first = sorted(classes.keys())[0]
            cls = classes[first]
            child_data = {"class": f"{cls.__module__}.{first}"}

        child_widget = ScriptNodeWidget(child_data, depth=self._depth + 1)
        child_widget.changed.connect(self._child_changed)

        wrapper = QtWidgets.QWidget()
        wrapper_layout = QtWidgets.QHBoxLayout()
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper.setLayout(wrapper_layout)
        wrapper_layout.addWidget(child_widget, stretch=1)

        # Only show remove button for list fields (single Script fields are always present)
        type_name = self._type_combo.currentText()
        classes = _get_script_classes()
        cls = classes.get(type_name)
        if cls is not None:
            field_info = cls.model_fields.get(field_name)
            if field_info is not None:
                _, inner = _is_optional(field_info.annotation)
                if get_origin(inner) is list:
                    remove_btn = QtWidgets.QToolButton()
                    remove_btn.setIcon(qa.icon("fa5s.minus"))
                    remove_btn.clicked.connect(lambda: self._remove_child(wrapper, child_widget))
                    wrapper_layout.addWidget(remove_btn, alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        # Insert before the add button for this field, or at end
        self._children_layout.addWidget(wrapper)
        self._child_widgets.append((field_name, child_widget))

    def _add_child_default(self, field_name: str):
        self._add_child(None, field_name)
        self._child_changed()

    def _remove_child(self, wrapper: QtWidgets.QWidget, child_widget: ScriptNodeWidget):
        self._child_widgets = [(fn, w) for fn, w in self._child_widgets if w is not child_widget]
        wrapper.deleteLater()
        self._child_changed()

    def _collect_children(self, cls: type):
        for field_name in _script_list_fields(cls):
            field_info = cls.model_fields[field_name]
            _, inner = _is_optional(field_info.annotation)
            children = [w.get_data() for fn, w in self._child_widgets if fn == field_name]
            if get_origin(inner) is list:
                self._data[field_name] = children
            else:
                self._data[field_name] = children[0] if children else {}

    @QtCore.Slot()
    def _child_changed(self):
        type_name = self._type_combo.currentText()
        classes = _get_script_classes()
        cls = classes.get(type_name)
        if cls is not None:
            self._collect_children(cls)
        self.changed.emit()

    def get_data(self) -> dict[str, Any]:
        return self._data
