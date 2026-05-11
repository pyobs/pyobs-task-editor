from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.backends import Backend
from pyobs_task_editor.edittaskwidget import EditTaskWidget


class TaskWidget(QtWidgets.QTabWidget):
    def __init__(self, backend: Backend):
        super().__init__()

        self._task: Task | None = None

        scroll_area_task = QtWidgets.QScrollArea()
        scroll_area_task.horizontalScrollBar().setVisible(False)
        self.tab_task = EditTaskWidget(backend)
        scroll_area_task.setWidgetResizable(True)
        scroll_area_task.setWidget(self.tab_task)
        self.addTab(scroll_area_task, "Task")

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self._task = task
        self.tab_task.set_task(self._task)

    def get_task(self) -> Task | None:
        return self._task
