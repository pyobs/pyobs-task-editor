from typing import cast

from PySide6 import QtWidgets, QtCore
import qtawesome as qa
from pyobs.robotic import Task
import inspect

from pyobs_task_editor.comboboxdialog import ComboBoxDialog


class ListWidget(QtWidgets.QGroupBox):
    item_selected = QtCore.Signal(Task)

    def __init__(self, title: str) -> None:
        super().__init__()

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

    @QtCore.Slot()
    def add_item(self):
        import pyobs.robotic.scheduler.constraints

        existing = [self.list_widget.item(row).text() for row in range(self.list_widget.count())]
        options = [
            name
            for name, obj in inspect.getmembers(pyobs.robotic.scheduler.constraints)
            if inspect.isclass(obj) and name not in existing
        ]

        dialog = ComboBoxDialog("Select type", options)
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            item = QtWidgets.QListWidgetItem()
            item.setText(dialog.option)
            self.list_widget.addItem(item)

    @QtCore.Slot()
    def remove_item(self):
        pass

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def _item_selected(self, item):
        import pyobs.robotic.scheduler.constraints

        print(item.text())
        klass = getattr(pyobs.robotic.scheduler.constraints, item.text())
        print(klass)
        print(klass.model_fields)

        layout = cast(QtWidgets.QFormLayout, self.edit_group.layout())
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)

        for name, info in klass.model_fields.items():
            if info.annotation is float:
                widget = QtWidgets.QDoubleSpinBox()
            else:
                widget = QtWidgets.QLineEdit()
            layout.addRow(name, widget)
            print(info.annotation)
