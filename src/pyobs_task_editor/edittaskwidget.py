from PySide6 import QtWidgets, QtCore
import qtawesome as qa
from pyobs.robotic import Task

from pyobs_task_editor.backends import Backend


class EditTaskWidget(QtWidgets.QWidget):
    task_changed = QtCore.Signal(Task)  # add this

    def __init__(self):
        super().__init__()

        self._task: Task | None = None
        self._backend: Backend | None = None
        self._updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        general = QtWidgets.QGroupBox("General")
        layout.addWidget(general)
        general_layout = QtWidgets.QFormLayout(general)
        self.active_widget = QtWidgets.QCheckBox("Active")
        self.active_widget.checkStateChanged.connect(self._update_task_from_gui)
        general_layout.addRow("", self.active_widget)
        self.task_id_widget = QtWidgets.QLineEdit()
        self.task_id_widget.setReadOnly(True)
        general_layout.addRow("ID", self.task_id_widget)
        self.task_name_widget = QtWidgets.QLineEdit()
        self.task_name_widget.textChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Name", self.task_name_widget)
        self.project_widget = QtWidgets.QComboBox()
        self.project_widget.setEditable(False)
        self.project_widget.currentTextChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Project", self.project_widget)

        # Duration row: spinbox + estimate button side by side
        duration_row = QtWidgets.QHBoxLayout()
        self.duration_widget = QtWidgets.QSpinBox()
        self.duration_widget.setMinimum(1)
        self.duration_widget.setMaximum(86400)
        self.duration_widget.valueChanged.connect(self._update_task_from_gui)
        duration_row.addWidget(self.duration_widget)
        self.estimate_button = QtWidgets.QToolButton()
        self.estimate_button.setIcon(qa.icon("mdi6.timer-play-outline"))
        self.estimate_button.setToolTip("Estimate duration from script")
        self.estimate_button.clicked.connect(self._estimate_duration)
        duration_row.addWidget(self.estimate_button)
        general_layout.addRow("Duration", duration_row)

        self.priority_widget = QtWidgets.QDoubleSpinBox()
        self.priority_widget.valueChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Priority", self.priority_widget)

    def set_backend(self, backend: Backend):
        self._backend = backend
        projects = [p.code for p in backend.get_projects()]
        self.project_widget.clear()
        self.project_widget.addItems(projects)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task

        self.active_widget.setChecked(task.active)
        self.task_id_widget.setText(task.id)
        self.task_name_widget.setText(task.name)
        if task.project == "":
            task.project = self.project_widget.currentText()
        self.project_widget.setCurrentText(task.project)
        self.duration_widget.setValue(task.duration)
        self.priority_widget.setValue(task.priority)

        self._updating = False

    @QtCore.Slot()
    def _update_task_from_gui(self):
        if self._task is None or self._updating:
            return
        self._task.active = self.active_widget.isChecked()
        self._task.name = self.task_name_widget.text()
        self._task.project = self.project_widget.currentText()
        self._task.duration = self.duration_widget.value()
        self._task.priority = self.priority_widget.value()
        self.task_changed.emit(self._task)

    @QtCore.Slot()
    def _estimate_duration(self):
        if self._task is None:
            return
        self.duration_widget.setValue(int(self._task.estimate_duration()))
