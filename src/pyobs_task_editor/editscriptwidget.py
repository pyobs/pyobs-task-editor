import io
import yaml
from PySide6 import QtWidgets, QtCore, QtGui
import inspect
import qtawesome as qa
import pyobs.robotic.scripts as scripts_module
from pydantic_core import PydanticUndefined
import pkgutil
import importlib
import pyobs.robotic.scripts as scripts_module

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
        action = toolbar.addAction(qa.icon("mdi6.file-import-outline"), "Insert template")
        action.triggered.connect(self._show_template_menu)
        self._template_btn = toolbar.widgetForAction(action)
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

    def _get_script_tree(self) -> dict:
        """Recursively discover all Script subclasses, preserving package structure."""
        from pyobs.robotic.task import Script

        def _scan(package) -> dict:
            results = {}
            for _, name, ispkg in pkgutil.iter_modules(package.__path__):
                full_name = f"{package.__name__}.{name}"
                try:
                    mod = importlib.import_module(full_name)
                except Exception:
                    continue
                if ispkg:
                    sub = _scan(mod)
                    if sub:
                        results[name] = sub
                else:
                    classes = {
                        n: o
                        for n, o in inspect.getmembers(mod)
                        if inspect.isclass(o)
                        and issubclass(o, Script)
                        and o is not Script
                        and o.__module__ == full_name
                    }
                    if classes:
                        results[name] = classes
            return results

        return _scan(scripts_module)

    def _build_script_menu(self, menu: QtWidgets.QMenu, tree: dict):
        """Recursively populate a QMenu from the script tree."""
        for name, value in sorted(tree.items()):
            if isinstance(value, dict) and all(isinstance(v, type) for v in value.values()):
                # Leaf: dict of class name → class
                for class_name, cls in sorted(value.items()):
                    action = menu.addAction(class_name)
                    action.triggered.connect(lambda checked=False, c=cls: self._insert_template(c))
            else:
                # Subpackage: recurse into a submenu
                submenu = menu.addMenu(name)
                self._build_script_menu(submenu, value)

    @QtCore.Slot()
    def _show_template_menu(self):
        tree = self._get_script_tree()
        menu = QtWidgets.QMenu(self)
        self._build_script_menu(menu, tree)
        pos = self._template_btn.mapToGlobal(self._template_btn.rect().bottomLeft())
        menu.exec(pos)

    def _insert_template(self, cls: type):
        from pydantic_core import PydanticUndefined

        template = {"class": f"{cls.__module__}.{cls.__name__}"}
        for field_name, field_info in cls.model_fields.items():
            if field_name in ("class", "exptime_done"):
                continue
            if field_info.default is not PydanticUndefined:
                template[field_name] = field_info.default
            elif field_info.default_factory is not None:
                template[field_name] = field_info.default_factory()
            else:
                template[field_name] = f"<{field_name}>"
        snippet = yaml.dump(template, default_flow_style=False)
        if not self.yaml_widget.toPlainText().strip():
            self.yaml_widget.setPlainText(snippet)
        else:
            self.yaml_widget.insertPlainText("\n" + snippet)
