from PySide6 import QtWidgets, QtCore
from astropy.time import Time

from pyobs.robotic import Task
from pyobs_task_editor.backends import Backend
from pyobs_task_editor.editschedulerwidget import EditSchedulerWidget
from pyobs_task_editor.editscriptwidget import EditScriptWidget
from pyobs_task_editor.edittargetwidget import EditTargetWidget
from pyobs_task_editor.edittaskwidget import EditTaskWidget
from pyobs_task_editor.observationlistwidget import ObservationListWidget


class TaskWidget(QtWidgets.QTabWidget):
    def __init__(self, backend: Backend):
        super().__init__()

        self._task: Task | None = None
        self._backend: Backend | None = backend

        self.tab_task = EditTaskWidget()
        self.addTab(self.tab_task, "Task")

        self.tab_scheduler = EditSchedulerWidget()
        self.addTab(self.tab_scheduler, "Schedule")

        self.tab_target = EditTargetWidget()
        self.addTab(self.tab_target, "Target")

        self.tab_script = EditScriptWidget()
        self.addTab(self.tab_script, "Script")

        self.tab_schedule = ObservationListWidget()
        self.addTab(self.tab_schedule, "Schedule")

        self.tab_observations = ObservationListWidget()
        self.addTab(self.tab_observations, "Observations")

    def set_backend(self, backend: Backend):
        self._backend = backend
        self.tab_task.set_backend(backend)

    @QtCore.Slot(list)
    def set_task(self, task: Task) -> None:
        self.setEnabled(task is not None)
        self._task = task
        self.tab_task.set_task(self._task)
        self.tab_scheduler.set_task(self._task)
        self.tab_target.set_task(self._task)
        self.tab_script.set_task(self._task)

        schedule = self._backend.get_observations(task=task, end_after=Time.now(), state="pending,in_progress")
        self.tab_schedule.set_observations(schedule)

        observations = self._backend.get_observations(
            task=task, end_before=Time.now(), state="completed,aborted,failed"
        )
        self.tab_observations.set_observations(observations)

    def get_task(self) -> Task | None:
        return self._task
