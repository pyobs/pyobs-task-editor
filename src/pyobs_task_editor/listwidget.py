from PySide6 import QtWidgets, QtCore
import qtawesome as qa
from pyobs.robotic import Task
import inspect


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

        edit_group = QtWidgets.QGroupBox()
        splitter.addWidget(edit_group)

    @QtCore.Slot()
    def add_item(self):
        import pyobs.robotic.scheduler.constraints

        items = [name for name, obj in inspect.getmembers(pyobs.robotic.scheduler.constraints) if inspect.isclass(obj)]
        print(items)

        item = QtWidgets.QListWidgetItem()
        item.setText("Add item")
        self.list_widget.addItem(item)

    @QtCore.Slot()
    def remove_item(self):
        pass
