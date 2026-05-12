from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.constraintmeritlistwidget import ConstraintMeritListWidget
import pyobs.robotic.scheduler.constraints
import pyobs.robotic.scheduler.merits


class EditSchedulerWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self._task: Task | None = None
        self._updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.constraints_widget = ConstraintMeritListWidget(
            "Constraints", pyobs.robotic.scheduler.constraints, "constraints"
        )
        layout.addWidget(self.constraints_widget)

        self.merits_widget = ConstraintMeritListWidget("Merits", pyobs.robotic.scheduler.merits, "merits")
        layout.addWidget(self.merits_widget)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task
        self.constraints_widget.set_task(task)
        self.merits_widget.set_task(task)
        self._updating = False
