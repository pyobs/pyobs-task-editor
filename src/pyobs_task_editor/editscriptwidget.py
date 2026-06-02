import io
import yaml
from PySide6 import QtWidgets, QtCore, QtGui

from pyobs.robotic import Task
from pyobs.robotic.task import Script


class EditScriptWidget(QtWidgets.QWidget):
    script_changed = QtCore.Signal(str)
    task_changed = QtCore.Signal(Task)

    def __init__(self):
        super().__init__()

        self._task: Task | None = None
        self._updating = False

        self.setLayout(QtWidgets.QVBoxLayout())
        group = QtWidgets.QGroupBox("Script")
        self.layout().addWidget(group)

        layout = QtWidgets.QVBoxLayout()
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

        self.status_label = QtWidgets.QLabel()
        layout.addWidget(self.status_label)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task
        if task is None or task.script is None:
            self.yaml_widget.clear()
            self.status_label.clear()
        else:
            with io.StringIO() as buffer:
                yaml.safe_dump(task.script, buffer)
                self.yaml_widget.setPlainText(buffer.getvalue())
            self._validate(task.script)
        self._updating = False

    @QtCore.Slot()
    def _text_changed(self) -> None:
        if self._updating:
            return
        try:
            raw = yaml.safe_load(self.yaml_widget.toPlainText()) or {}
        except yaml.YAMLError as e:
            self.status_label.setText(f"✗ Invalid YAML: {e}")
            self.status_label.setStyleSheet("color: red;")
            return
        self._validate(raw)
        self._task.script = raw
        self.script_changed.emit(self.yaml_widget.toPlainText())
        self.task_changed.emit(self._task)

    def _validate(self, raw: dict):
        try:
            Script.model_validate(raw)
            self.status_label.setText("✓ Valid")
            self.status_label.setStyleSheet("color: green;")
        except Exception as e:
            self.status_label.setText(f"✗ {e}")
            self.status_label.setStyleSheet("color: red;")
