from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.constraintmeritlistwidget import ConstraintMeritListWidget
import pyobs.robotic.scheduler.constraints
import pyobs.robotic.scheduler.merits


class EditTaskWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self._task: Task | None = None

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        general = QtWidgets.QGroupBox("General")
        layout.addWidget(general)
        general_layout = QtWidgets.QFormLayout(general)
        self.task_id = QtWidgets.QLineEdit()
        self.task_id.setReadOnly(True)
        general_layout.addRow("ID", self.task_id)
        self.task_name = QtWidgets.QLineEdit()
        self.task_name.textChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Name", self.task_name)
        self.project = QtWidgets.QLineEdit()
        self.project.textChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Project", self.project)
        self.duration = QtWidgets.QSpinBox()
        self.duration.valueChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Duration", self.duration)
        self.priority = QtWidgets.QDoubleSpinBox()
        self.priority.valueChanged.connect(self._update_task_from_gui)
        general_layout.addRow("Priority", self.priority)

        self.constraints = ConstraintMeritListWidget("Constraints", pyobs.robotic.scheduler.constraints, "constraints")
        layout.addWidget(self.constraints)

        self.merits = ConstraintMeritListWidget("Merits", pyobs.robotic.scheduler.merits, "merits")
        layout.addWidget(self.merits)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._task = task

        self.task_id.setText(task.id)
        self.task_name.setText(task.name)
        self.project.setText(task.project)
        self.duration.setValue(task.duration)
        self.priority.setValue(task.priority)

        self.constraints.set_task(task)
        self.merits.set_task(task)

    @QtCore.Slot()
    def _update_task_from_gui(self):
        if self._task is None:
            return
        self._task.name = self.task_name.text()
        self._task.project = self.project.text()
        self._task.duration = self.duration.value()
        self._task.priority = self.priority.value()
