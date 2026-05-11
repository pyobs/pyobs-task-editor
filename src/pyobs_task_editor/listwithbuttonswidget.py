from PySide6 import QtWidgets, QtCore
import qtawesome as qa


class ListWithButtonsWidget(QtWidgets.QWidget):
    add_clicked = QtCore.Signal()
    remove_clicked = QtCore.Signal()
    item_selected = QtCore.Signal(str)

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.currentTextChanged.connect(lambda t: self.item_selected.emit(t))
        layout.addWidget(self.list_widget)

        buttons_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(buttons_layout)

        buttons_layout.addSpacerItem(
            QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        )

        self.button_add = QtWidgets.QToolButton()
        self.button_add.setIcon(qa.icon("fa5s.plus"))
        self.button_add.clicked.connect(lambda: self.add_clicked.emit())
        buttons_layout.addWidget(self.button_add)

        # self.button_remove = QtWidgets.QToolButton()
        # self.button_remove.setIcon(qa.icon("fa5s.minus"))
        # self.button_remove.clicked.connect(lambda: self.remove_clicked.emit())
        # buttons_layout.addWidget(self.button_remove)

    def __getattr__(self, item):
        return self.list_widget.__getattribute__(item)
