from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.backends import Backend
from pyobs_task_editor.constraintmeritlistwidget import ConstraintMeritListWidget
import pyobs.robotic.scheduler.constraints
import pyobs.robotic.scheduler.merits
from pyobs_task_editor.edittargetwidget import EditTargetWidget


class EditTaskWidget(QtWidgets.QWidget):
    def __init__(self, backend: Backend):
        super().__init__()

        self._task: Task | None = None
        self._updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        projects = [p.code for p in backend.get_projects()]

        general = QtWidgets.QGroupBox("General")
        layout.addWidget(general)
        general_layout = QtWidgets.QFormLayout(general)
        self.task_id_widget = QtWidgets.QLineEdit()
        self.task_id_widget.setReadOnly(True)
        general_layout.addRow("ID", self.task_id_widget)
        self.task_name_widget = QtWidgets.QLineEdit()
        self.task_name_widget.textChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Name", self.task_name_widget)
        self.project_widget = QtWidgets.QComboBox()
        self.project_widget.setEditable(False)
        self.project_widget.addItems(projects)
        self.project_widget.currentTextChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Project", self.project_widget)
        self.duration_widget = QtWidgets.QSpinBox()
        self.duration_widget.valueChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Duration", self.duration_widget)
        self.priority_widget = QtWidgets.QDoubleSpinBox()
        self.priority_widget.valueChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Priority", self.priority_widget)

        self.constraints_widget = ConstraintMeritListWidget(
            "Constraints", pyobs.robotic.scheduler.constraints, "constraints"
        )
        layout.addWidget(self.constraints_widget)

        self.merits_widget = ConstraintMeritListWidget("Merits", pyobs.robotic.scheduler.merits, "merits")
        layout.addWidget(self.merits_widget)

        self.target_widget = EditTargetWidget(backend)
        self.target_widget.target_changed.connect(self._update_target)
        layout.addWidget(self.target_widget)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task

        self.task_id_widget.setText(task.id)
        self.task_name_widget.setText(task.name)
        self.project_widget.setCurrentText(task.project)
        self.duration_widget.setValue(task.duration)
        self.priority_widget.setValue(task.priority)

        self.constraints_widget.set_task(task)
        self.merits_widget.set_task(task)
        self.target_widget.set_target(task.target)

        self._updating = False

    @QtCore.Slot()
    def _update_task_from_gui(self):
        if self._task is None or self._updating:
            return
        self._task.name = self.task_name_widget.text()
        self._task.project = self.project_widget.currentText()
        self._task.duration = self.duration_widget.value()
        self._task.priority = self.priority_widget.value()

    @QtCore.Slot()
    def _update_target(self) -> None:
        if self._task is None or self._updating:
            return
        self._task.target = self.target_widget.target
