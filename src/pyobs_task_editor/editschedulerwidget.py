from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.constraintmeritlistwidget import ConstraintMeritListWidget
import pyobs.robotic.scheduler.constraints
import pyobs.robotic.scheduler.merits


class EditSchedulerWidget(QtWidgets.QWidget):
    task_changed = QtCore.Signal(Task)

    def __init__(self):
        super().__init__()

        self._task: Task | None = None
        self._updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.constraints_widget = ConstraintMeritListWidget(
            "Constraints", pyobs.robotic.scheduler.constraints, "constraints"
        )
        self.constraints_widget.task_changed.connect(self._on_changed)
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

    @QtCore.Slot()
    def _on_changed(self):  # add this
        if not self._updating and self._task is not None:
            self.task_changed.emit(self._task)
