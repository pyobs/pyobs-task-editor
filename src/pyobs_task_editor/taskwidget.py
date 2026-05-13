from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.backends import Backend
from pyobs_task_editor.editschedulerwidget import EditSchedulerWidget
from pyobs_task_editor.editscriptwidget import EditScriptWidget
from pyobs_task_editor.edittargetwidget import EditTargetWidget
from pyobs_task_editor.edittaskwidget import EditTaskWidget


class TaskWidget(QtWidgets.QTabWidget):
    def __init__(self, backend: Backend):
        super().__init__()

        self._task: Task | None = None

        self.tab_task = EditTaskWidget()
        self.addTab(self.tab_task, "Task")

        self.tab_scheduler = EditSchedulerWidget()
        self.addTab(self.tab_scheduler, "Schedule")

        self.tab_target = EditTargetWidget()
        self.addTab(self.tab_target, "Target")

        self.tab_script = EditScriptWidget()
        self.addTab(self.tab_script, "Script")

    def set_backend(self, backend: Backend):
        self.tab_task.set_backend(backend)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self.setEnabled(task is not None)
        self._task = task
        self.tab_task.set_task(self._task)
        self.tab_scheduler.set_task(self._task)
        self.tab_target.set_task(self._task)
        self.tab_script.set_task(self._task)

    def get_task(self) -> Task | None:
        return self._task
