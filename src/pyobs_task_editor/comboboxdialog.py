from PySide6 import QtWidgets


class ComboBoxDialog(QtWidgets.QDialog):
    def __init__(self, title: str, options: list[str]) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.resize(400, 20)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.combo_box = QtWidgets.QComboBox()
        self.combo_box.addItems(options)
        self.layout().addWidget(self.combo_box)
        self.button = QtWidgets.QPushButton("OK")
        self.layout().addWidget(self.button)
        self.button.clicked.connect(self.accept)

    @property
    def option(self) -> str:
        return self.combo_box.currentText()
