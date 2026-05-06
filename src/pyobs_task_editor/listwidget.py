from PySide6 import QtWidgets, QtCore, QtGui
import qtawesome as qa
from pyobs.robotic import Task


class DetailListWidgetItem(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QtWidgets.QFormLayout()
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.setLayout(layout)
        self.setMinimumHeight(100)

        self.type = QtWidgets.QComboBox()
        layout.addRow("Type", self.type)

        self.test = QtWidgets.QLineEdit()
        layout.addRow("Test", self.test)


class ListWidget(QtWidgets.QGroupBox):
    item_selected = QtCore.Signal(Task)

    def __init__(self, title: str) -> None:
        super().__init__()

        self.setTitle(title)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        buttons_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(buttons_layout)

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

    @QtCore.Slot()
    def add_item(self):
        item = QtWidgets.QListWidgetItem()
        self.list_widget.addItem(item)
        widget = DetailListWidgetItem()
        item.setSizeHint(widget.minimumSizeHint())
        self.list_widget.setItemWidget(item, widget)

    @QtCore.Slot()
    def remove_item(self):
        pass
