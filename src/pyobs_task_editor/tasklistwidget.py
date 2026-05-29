from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task
from pyobs_task_editor.tasktreemodel import TaskTreeModel


class TaskListWidget(QtWidgets.QWidget):
    task_selected = QtCore.Signal(Task)

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.task_tree = QtWidgets.QTreeView()
        self.task_tree.setHeaderHidden(True)
        layout.addWidget(self.task_tree)

    def set_model(self, model: TaskTreeModel):
        self._model = model
        self.task_tree.setModel(model)
        self.task_tree.selectionModel().currentChanged.connect(self._selection_changed)

    def set_tasks(self, tasks: list[Task]):
        self._model.set_tasks(tasks)
        self.task_tree.expandAll()
        # Select the first task if any exist
        first = self._model.index(0, 0, QtCore.QModelIndex())  # first project
        first_task = self._model.index(0, 0, first)  # first task under it
        if first_task.isValid():
            self.task_tree.selectionModel().setCurrentIndex(first_task, QtCore.QItemSelectionModel.ClearAndSelect)

    def add_task(self, task: Task):
        self._model.add_task(task)
        self.task_tree.expandAll()
        idx = self._model.index_of(task)
        if idx.isValid():
            self.task_tree.selectionModel().setCurrentIndex(idx, QtCore.QItemSelectionModel.ClearAndSelect)

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _selection_changed(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        task = current.data(QtCore.Qt.UserRole)
        if task is not None:
            self.task_selected.emit(task)
