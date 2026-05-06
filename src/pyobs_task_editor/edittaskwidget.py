from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.listwidget import ListWidget


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
        general_layout.addRow("ID", self.task_id)
        self.task_name = QtWidgets.QLineEdit()
        general_layout.addRow("Name", self.task_name)
        self.project = QtWidgets.QLineEdit()
        general_layout.addRow("Project", self.project)
        self.duration = QtWidgets.QSpinBox()
        general_layout.addRow("Duration", self.duration)
        self.priority = QtWidgets.QDoubleSpinBox()
        general_layout.addRow("Priority", self.priority)

        self.constraints = ListWidget("Constraints")
        layout.addWidget(self.constraints)

        self.merits = ListWidget("Merits")
        layout.addWidget(self.merits)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._task = task

        self.task_id.setText(task.id)
        self.task_name.setText(task.name)
        self.project.setText(task.project)
        self.duration.setValue(task.duration)
        self.priority.setValue(task.priority)
