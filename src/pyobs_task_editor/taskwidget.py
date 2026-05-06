from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.edittaskwidget import EditTaskWidget


class TaskWidget(QtWidgets.QTabWidget):
    def __init__(self):
        super().__init__()

        self._task: Task | None = None

        self.tab_task = EditTaskWidget()
        self.addTab(self.tab_task, "Task")

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._task = task
        self.tab_task.set_task(self._task)
