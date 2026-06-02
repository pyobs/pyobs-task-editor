import datetime
import functools

from astropy.time import Time
from typing import cast, get_origin, Literal, get_args

from PySide6 import QtWidgets, QtCore
import qtawesome as qa
from pyobs.robotic import Task
import inspect

from pyobs_task_editor.comboboxdialog import ComboBoxDialog

IGNORED_FIELDS = {"cost", "target_dependent"}


class ConstraintMeritListWidget(QtWidgets.QGroupBox):
    item_selected = QtCore.Signal(Task)
    task_changed = QtCore.Signal()

    def __init__(self, title: str, module, name) -> None:
        super().__init__()

        self._task: Task | None = None
        self._module = module
        self._name = name

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

        existing = [self.list_widget.item(row).text() for row in range(self.list_widget.count())]
        options = [
            name for name, obj in inspect.getmembers(self._module) if inspect.isclass(obj) and name not in existing
        ]
        options.remove(self._name.capitalize()[:-1])

        dialog = ComboBoxDialog("Select type", options)
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            obj = getattr(self._module, dialog.option)()
            getattr(self._task, self._name).append(obj)
            self.update_list(dialog.option)
            self.task_changed.emit()

    @QtCore.Slot()
    def remove_item(self):
        pass

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _item_selected(self, item):
        layout = cast(QtWidgets.QFormLayout, self.edit_group.layout())
        while layout.rowCount() > 0:
            layout.removeRow(0)

        if item is None:
            return

        obj = item.data(QtCore.Qt.UserRole)
        for name, info in obj.model_fields.items():
            if name in IGNORED_FIELDS:
                continue

            if info.annotation in [float, int]:
                widget = QtWidgets.QDoubleSpinBox() if info.annotation is float else QtWidgets.QSpinBox()
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
                widget.setValue(getattr(obj, name))
                widget.valueChanged.connect(functools.partial(self._value_changed, obj, name))
            elif info.annotation == Time:
                widget = QtWidgets.QDateTimeEdit()
                widget.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
                widget.setCalendarPopup(True)
                widget.setDateTime(getattr(obj, name).to_datetime())
                widget.dateTimeChanged.connect(functools.partial(self._value_changed, obj, name))
            elif get_origin(info.annotation) is Literal:
                widget = QtWidgets.QComboBox()
                widget.addItems([str(a) for a in get_args(info.annotation)])
                widget.setCurrentText(str(getattr(obj, name)))
                widget.currentTextChanged.connect(functools.partial(self._value_changed, obj, name))
            else:
                widget = QtWidgets.QLineEdit()
                widget.setText(getattr(obj, name))
                widget.textChanged.connect(functools.partial(self._value_changed, obj, name))
            layout.addRow(name, widget)

    @QtCore.Slot(float)
    @QtCore.Slot(str)
    @QtCore.Slot(datetime.datetime)
    def _value_changed(self, obj, name, value):
        setattr(obj, name, value)
        self.task_changed.emit()
