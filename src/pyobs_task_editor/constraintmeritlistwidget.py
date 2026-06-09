import functools
import inspect

from typing import cast, get_origin

from PySide6 import QtWidgets, QtCore
import qtawesome as qa
from pyobs.robotic import Task

from pyobs_task_editor.comboboxdialog import ComboBoxDialog
from pyobs_task_editor.modelwidgets import _make_widget, _get_widget_value

IGNORED_FIELDS = {"cost", "target_dependent"}


class ConstraintMeritListWidget(QtWidgets.QGroupBox):
    item_selected = QtCore.Signal(Task)
    task_changed = QtCore.Signal()

    def __init__(self, title: str, module, name) -> None:
        super().__init__()

        self._task: Task | None = None
        self._module = module
        self._name = name
        self._field_widgets: dict[str, QtWidgets.QWidget] = {}
        self._current_obj = None

        self.setTitle(title)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        splitter = QtWidgets.QSplitter()
        layout.addWidget(splitter)

        list_frame = QtWidgets.QWidget()
        splitter.addWidget(list_frame)
        list_layout = QtWidgets.QVBoxLayout()
        list_frame.setLayout(list_layout)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.currentItemChanged.connect(self._item_selected)
        list_layout.addWidget(self.list_widget)

        buttons_layout = QtWidgets.QHBoxLayout()
        list_layout.addLayout(buttons_layout)

        buttons_layout.addSpacerItem(
            QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        )

        self.button_add = QtWidgets.QToolButton()
        self.button_add.setIcon(qa.icon("fa5s.plus"))
        self.button_add.clicked.connect(self.add_item)
        buttons_layout.addWidget(self.button_add)

        self.button_remove = QtWidgets.QToolButton()
        self.button_remove.setIcon(qa.icon("fa5s.minus"))
        self.button_remove.clicked.connect(self.remove_item)
        buttons_layout.addWidget(self.button_remove)

        self.edit_group = QtWidgets.QGroupBox()
        self.edit_group.setLayout(QtWidgets.QFormLayout())
        splitter.addWidget(self.edit_group)

        splitter.setSizes([splitter.width() // 2, splitter.width() // 2])

    @QtCore.Slot(Task)
    def set_task(self, task: Task) -> None:
        self._task = task
        self.update_list()

    @QtCore.Slot(str)
    def update_list(self, selected: str = ""):
        if self._task is None:
            return
        self.list_widget.clear()
        row = 0
        for i, obj in enumerate(getattr(self._task, self._name)):
            item = QtWidgets.QListWidgetItem()
            item.setText(obj.__class__.__name__)
            item.setData(QtCore.Qt.UserRole, obj)
            self.list_widget.addItem(item)
            if obj.__class__.__name__ == selected:
                row = i
        self.list_widget.setCurrentRow(row)

    @QtCore.Slot()
    def add_item(self):
        if self._task is None:
            return

        from pydantic_core import PydanticUndefined

        existing = [self.list_widget.item(row).text() for row in range(self.list_widget.count())]
        options = [
            name for name, obj in inspect.getmembers(self._module) if inspect.isclass(obj) and name not in existing
        ]
        options.remove(self._name.capitalize()[:-1])

        dialog = ComboBoxDialog("Select type", options)
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            cls = getattr(self._module, dialog.option)
            kwargs = {}
            for field_name, field_info in cls.model_fields.items():
                if field_info.default is not PydanticUndefined:
                    continue
                if field_info.default_factory is not None:
                    kwargs[field_name] = field_info.default_factory()
                elif get_origin(field_info.annotation) is list:
                    kwargs[field_name] = []
            obj = cls(**kwargs)
            getattr(self._task, self._name).append(obj)
            self.update_list(dialog.option)
            self.task_changed.emit()

    @QtCore.Slot()
    def remove_item(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        obj = item.data(QtCore.Qt.UserRole)
        getattr(self._task, self._name).remove(obj)
        self.update_list()
        self.task_changed.emit()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _item_selected(self, item):
        layout = cast(QtWidgets.QFormLayout, self.edit_group.layout())
        while layout.rowCount() > 0:
            layout.removeRow(0)

        self._field_widgets.clear()
        self._current_obj = None

        if item is None:
            return

        obj = item.data(QtCore.Qt.UserRole)
        self._current_obj = obj

        for name, info in obj.model_fields.items():
            if name in IGNORED_FIELDS:
                continue
            value = getattr(obj, name)
            widget = _make_widget(info.annotation, value, functools.partial(self._value_changed, obj, name))
            if widget is not None:
                self._field_widgets[name] = widget
                # Apply ge/le metadata to spinboxes
                if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
                    for meta in info.metadata:
                        if hasattr(meta, "ge"):
                            widget.setMinimum(meta.ge)
                        if hasattr(meta, "le"):
                            widget.setMaximum(meta.le)
                    if (
                        isinstance(widget, QtWidgets.QDoubleSpinBox)
                        and info.json_schema_extra is not None
                        and "decimals" in info.json_schema_extra
                    ):
                        widget.setDecimals(info.json_schema_extra["decimals"])
                layout.addRow(name, widget)

    @QtCore.Slot()
    def _value_changed(self, obj, name, value=None):
        field_info = obj.model_fields.get(name)
        if field_info is not None:
            widget = self._field_widgets.get(name)
            if widget is not None:
                extracted = _get_widget_value(widget, field_info.annotation)
                if extracted is not None:
                    value = extracted
        if value is not None:
            setattr(obj, name, value)
        self.task_changed.emit()
