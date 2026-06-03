from __future__ import annotations
import yaml
from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs.robotic.task import Script

from .scriptnodewidget import ScriptNodeWidget


class EditScriptWidget(QtWidgets.QWidget):
    script_changed = QtCore.Signal(str)
    task_changed = QtCore.Signal(Task)

    def __init__(self):
        super().__init__()

        self._task: Task | None = None
        self._updating = False
        self._node_widget: ScriptNodeWidget | None = None

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # Toggle between visual and YAML editor
        toggle_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(toggle_layout)
        self._visual_btn = QtWidgets.QRadioButton("Visual")
        self._visual_btn.setChecked(True)
        self._yaml_btn = QtWidgets.QRadioButton("YAML")
        self._visual_btn.toggled.connect(self._mode_changed)
        toggle_layout.addWidget(self._visual_btn)
        toggle_layout.addWidget(self._yaml_btn)
        toggle_layout.addStretch()

        # Stack: visual editor on page 0, YAML editor on page 1
        self._stack = QtWidgets.QStackedWidget()
        main_layout.addWidget(self._stack)

        # Page 0: visual editor in a scroll area
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._stack.addWidget(self._scroll)

        # Page 1: YAML editor
        yaml_page = QtWidgets.QWidget()
        yaml_layout = QtWidgets.QVBoxLayout(yaml_page)
        yaml_layout.setContentsMargins(0, 0, 0, 0)
        self._yaml_edit = QtWidgets.QPlainTextEdit()
        self._yaml_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        font = self._yaml_edit.document().defaultFont()
        font.setFamily("Courier New")
        self._yaml_edit.document().setDefaultFont(font)
        self._yaml_edit.textChanged.connect(self._yaml_edited)
        yaml_layout.addWidget(self._yaml_edit)
        self._status_label = QtWidgets.QLabel()
        yaml_layout.addWidget(self._status_label)
        self._stack.addWidget(yaml_page)

    @QtCore.Slot(Task)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task
        self._reload()
        self._updating = False

    def _reload(self):
        if self._task is None or not self._task.script:
            data = {}
        else:
            data = self._task.script

        # Rebuild visual editor
        if self._node_widget is not None:
            self._node_widget.deleteLater()
        if data:
            self._node_widget = ScriptNodeWidget(data)
            self._node_widget.changed.connect(self._visual_changed)
        else:
            self._node_widget = None
        container = self._node_widget if self._node_widget else QtWidgets.QWidget()
        self._scroll.setWidget(container)

        # Reload YAML editor
        self._yaml_edit.setPlainText(yaml.dump(data, default_flow_style=False) if data else "")
        self._validate_yaml(data)

    @QtCore.Slot(bool)
    def _mode_changed(self, visual: bool):
        self._stack.setCurrentIndex(0 if visual else 1)
        if not visual:
            # Sync YAML from visual
            data = self._node_widget.get_data() if self._node_widget else {}
            self._yaml_edit.setPlainText(yaml.dump(data, default_flow_style=False) if data else "")

    @QtCore.Slot()
    def _visual_changed(self):
        if self._updating or self._task is None or self._node_widget is None:
            return
        self._task.script = self._node_widget.get_data()
        self.script_changed.emit(yaml.dump(self._task.script))
        self.task_changed.emit(self._task)

    @QtCore.Slot()
    def _yaml_edited(self):
        if self._updating or self._task is None:
            return
        try:
            raw = yaml.safe_load(self._yaml_edit.toPlainText()) or {}
        except yaml.YAMLError as e:
            self._status_label.setText(f"✗ Invalid YAML: {e}")
            self._status_label.setStyleSheet("color: red;")
            return
        self._validate_yaml(raw)
        self._task.script = raw
        self.script_changed.emit(self._yaml_edit.toPlainText())
        self.task_changed.emit(self._task)

    def _validate_yaml(self, raw: dict):
        try:
            if raw:
                Script.model_validate(raw)
            self._status_label.setText("✓ Valid" if raw else "")
            self._status_label.setStyleSheet("color: green;")
        except Exception as e:
            self._status_label.setText(f"✗ {e}")
            self._status_label.setStyleSheet("color: red;")
