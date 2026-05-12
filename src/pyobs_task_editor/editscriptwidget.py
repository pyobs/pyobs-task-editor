from PySide6 import QtWidgets, QtCore, QtGui

from pyobs_task_editor.backends import Backend


class EditScriptWidget(QtWidgets.QGroupBox):
    script_changed = QtCore.Signal(str)

    def __init__(self, backend: Backend):
        super().__init__()

        self._updating = False

        self.setTitle("Script")
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.yaml_widget = QtWidgets.QPlainTextEdit()
        self.yaml_widget.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.yaml_widget.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.yaml_widget.setMinimumHeight(200)
        font = self.yaml_widget.document().defaultFont()
        font.setFamily("Courier New")
        self.yaml_widget.document().setDefaultFont(font)
        self.yaml_widget.textChanged.connect(self._text_changed)
        layout.addWidget(self.yaml_widget)

    @QtCore.Slot(str)
    def set_script(self, script: str | None) -> None:
        self._updating = True
        if script is None:
            self.yaml_widget.clear()
        else:
            self.yaml_widget.setPlainText(script)
        self._updating = False

    @QtCore.Slot(str)
    def _text_changed(self, script: str) -> None:
        if not self._updating:
            self.script_changed.emit(self.yaml_widget.toPlainText())
