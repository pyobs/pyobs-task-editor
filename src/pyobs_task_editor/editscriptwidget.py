import io
import yaml
from PySide6 import QtWidgets, QtCore, QtGui
import inspect
import qtawesome as qa
import pyobs.robotic.scripts as scripts_module
from pydantic_core import PydanticUndefined

from pyobs.robotic import Task
from pyobs.robotic.task import Script
from pyobs_task_editor.yamleditor import YamlEditor


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

        toolbar = QtWidgets.QToolBar()
        toolbar.setIconSize(QtCore.QSize(16, 16))
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        action = toolbar.addAction(qa.icon("mdi6.file-import-outline"), "Insert script template")
        action.triggered.connect(self._insert_template)
        layout.addWidget(toolbar)

        self.yaml_widget = YamlEditor()
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

    def _get_script_classes(self) -> dict[str, type]:
        from pyobs.robotic.task import Script

        return {
            name: obj
            for name, obj in inspect.getmembers(scripts_module)
            if inspect.isclass(obj) and issubclass(obj, Script) and name != "Script"
        }

    def _build_template(self, cls: type) -> dict:
        from pyobs.robotic.task import Script
        import typing

        result = {"class": f"{cls.__module__}.{cls.__name__}"}
        for field_name, field_info in cls.model_fields.items():
            if field_name in ("class", "exptime_done"):
                continue
            if field_info.default is not PydanticUndefined:
                result[field_name] = field_info.default
            elif field_info.default_factory is not None:
                val = field_info.default_factory()
                # For script list fields, insert one empty child template
                ann = field_info.annotation
                origin = typing.get_origin(ann)
                args = typing.get_args(ann)
                if origin is list and len(args) == 1 and inspect.isclass(args[0]) and issubclass(args[0], Script):
                    first_cls = list(self._get_script_classes().values())[0]
                    val = [self._build_template(first_cls)]
                result[field_name] = val
            else:
                # Required field — insert a placeholder comment
                result[field_name] = f"<{field_name}>"
        return result

    @QtCore.Slot()
    def _insert_template(self):
        classes = self._get_script_classes()
        name, ok = QtWidgets.QInputDialog.getItem(
            self, "Insert template", "Script type:", sorted(classes.keys()), editable=False
        )
        if not ok:
            return
        template = self._build_template(classes[name])
        snippet = yaml.dump(template, default_flow_style=False)
        # Replace content if empty, otherwise insert at cursor
        if not self.yaml_widget.toPlainText().strip():
            self.yaml_widget.setPlainText(snippet)
        else:
            self.yaml_widget.insertPlainText("\n" + snippet)
