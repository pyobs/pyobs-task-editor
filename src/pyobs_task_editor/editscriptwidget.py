import io

import yaml
from PySide6 import QtWidgets, QtCore, QtGui

from pyobs.robotic import Task
from pyobs_task_editor.backends import Backend


class EditScriptWidget(QtWidgets.QWidget):
    script_changed = QtCore.Signal(str)

    def __init__(self, backend: Backend):
        super().__init__()

        self._task: Task | None = None
        self._updating = False

        self.setLayout(QtWidgets.QVBoxLayout())
        group = QtWidgets.QGroupBox("Script")
        self.layout().addWidget(group)

        layout = QtWidgets.QFormLayout()
        group.setLayout(layout)

        self.yaml_widget = QtWidgets.QPlainTextEdit()
        self.yaml_widget.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.yaml_widget.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.yaml_widget.setMinimumHeight(200)
        font = self.yaml_widget.document().defaultFont()
        font.setFamily("Courier New")
        self.yaml_widget.document().setDefaultFont(font)
        self.yaml_widget.textChanged.connect(self._text_changed)
        layout.addWidget(self.yaml_widget)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task
        if task is None or task.script is None:
            self.yaml_widget.clear()
        else:
            with io.StringIO() as buffer:
                yaml.safe_dump(task.script, buffer)
                self.yaml_widget.setPlainText(buffer.getvalue())
        self._updating = False

    @QtCore.Slot()
    def _text_changed(self) -> None:
        if not self._updating:
            self.script_changed.emit(self.yaml_widget.toPlainText())
