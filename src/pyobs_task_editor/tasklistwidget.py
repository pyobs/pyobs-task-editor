from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task


class TaskListWidget(QtWidgets.QWidget):
    task_selected = QtCore.Signal(Task)

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.task_list = QtWidgets.QListWidget()
        self.task_list.currentItemChanged.connect(self._selection_changed)
        layout.addWidget(self.task_list)

    @QtCore.Slot(list)
    def set_tasks(self, tasks: list[Task]):
        self.task_list.clear()
        for task in tasks:
            item = QtWidgets.QListWidgetItem(task.name)
            item.setData(QtCore.Qt.UserRole, task)
            self.task_list.addItem(item)
        if len(tasks) > 0:
            self.task_list.setCurrentRow(0)

    @QtCore.Slot()
    def _selection_changed(self):
        item = self.task_list.item(self.task_list.currentRow())
        if item is not None:
            self.task_selected.emit(item.data(QtCore.Qt.UserRole))

    def add_task(self, task: Task):
        item = QtWidgets.QListWidgetItem(task.name)
        item.setData(QtCore.Qt.UserRole, task)
        self.task_list.addItem(item)
        self.task_list.setCurrentItem(item)

    def __getattr__(self, item):
        return self.task_list.__getattribute__(item)
