import qtawesome as qa
from PySide6 import QtCore, QtGui
from pyobs.robotic import Task


def _encode(project_idx: int, task_idx: int) -> int:
    # task_idx == -1 means this is a project row; store as 0 offset
    return project_idx * 10000 + (task_idx + 1)


def _decode(ptr: int) -> tuple[int, int]:
    task_idx = (ptr % 10000) - 1
    project_idx = ptr // 10000
    return project_idx, task_idx


class TaskTreeModel(QtCore.QAbstractItemModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list[str] = []
        self._tasks: dict[str, list[Task]] = {}
        self._dirty: set[str] = set()  # add this

    def set_tasks(self, tasks: list[Task]):
        self.beginResetModel()
        self._set_tasks(tasks)
        self._dirty.clear()  # add this
        self.endResetModel()

    def mark_dirty(self, task: Task):
        self._dirty.add(task.id)

    def mark_clean(self, task: Task):
        self._dirty.discard(task.id)

    def is_dirty(self, task: Task) -> bool:
        return task.id in self._dirty

    def _set_tasks(self, tasks: list[Task]):
        self._projects = []
        self._tasks = {}
        for task in tasks:
            if task.project not in self._tasks:
                self._projects.append(task.project)
                self._tasks[task.project] = []
            self._tasks[task.project].append(task)

    def add_task(self, task: Task):
        if task.project not in self._tasks:
            project_row = len(self._projects)
            self.beginInsertRows(QtCore.QModelIndex(), project_row, project_row)
            self._projects.append(task.project)
            self._tasks[task.project] = [task]
            self.endInsertRows()
        else:
            project_row = self._projects.index(task.project)
            project_index = self.createIndex(project_row, 0, _encode(project_row, -1))
            task_row = len(self._tasks[task.project])
            self.beginInsertRows(project_index, task_row, task_row)
            self._tasks[task.project].append(task)
            self.endInsertRows()

    def update_task(self, task: Task):
        # Find the task by ID across all projects (ignoring task.project,
        # which may already have been updated in the GUI)
        old_project = None
        for project, tasks in self._tasks.items():
            for t in tasks:
                if t.id == task.id:
                    old_project = project
                    break
            if old_project is not None:
                break

        if old_project is None:
            return

        self.mark_dirty(task)

        if old_project == task.project:
            # Project unchanged — fast path, just repaint
            idx = self.index_of(task)
            if idx.isValid():
                self.dataChanged.emit(idx, idx, [QtCore.Qt.DisplayRole, QtCore.Qt.ForegroundRole])
        else:
            # Project changed — update stored data and reset
            self.beginResetModel()
            self._tasks[old_project] = [t for t in self._tasks[old_project] if t.id != task.id]
            if not self._tasks[old_project]:
                self._projects.remove(old_project)
                del self._tasks[old_project]
            if task.project not in self._tasks:
                self._projects.append(task.project)
                self._tasks[task.project] = []
            self._tasks[task.project].append(task)
            self.endResetModel()

    def index_of(self, task: Task) -> QtCore.QModelIndex:
        if task.project not in self._tasks:
            return QtCore.QModelIndex()
        project_row = self._projects.index(task.project)
        for task_row, t in enumerate(self._tasks[task.project]):
            if t.id == task.id:
                return self.createIndex(task_row, 0, _encode(project_row, task_row))
        return QtCore.QModelIndex()

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            return self.createIndex(row, column, _encode(row, -1))
        project_idx, _ = _decode(parent.internalId())
        return self.createIndex(row, column, _encode(project_idx, row))

    def parent(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        project_idx, task_idx = _decode(index.internalId())
        if task_idx == -1:
            return QtCore.QModelIndex()
        return self.createIndex(project_idx, 0, _encode(project_idx, -1))

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._projects)
        project_idx, task_idx = _decode(parent.internalId())
        if task_idx == -1:
            return len(self._tasks[self._projects[project_idx]])
        return 0

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 1

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> object:
        if not index.isValid():
            return None
        project_idx, task_idx = _decode(index.internalId())
        if role == QtCore.Qt.DisplayRole:
            if task_idx == -1:
                return self._projects[project_idx]
            return self._tasks[self._projects[project_idx]][task_idx].name
        if task_idx != -1:
            task = self._tasks[self._projects[project_idx]][task_idx]
            if role == QtCore.Qt.UserRole:
                return task
            if role == QtCore.Qt.ForegroundRole and not task.active:
                return QtGui.QColor(QtCore.Qt.GlobalColor.gray)
            if role == QtCore.Qt.DecorationRole and task.id in self._dirty:
                return QtGui.QIcon(qa.icon("mdi6.circle-small", color="orange"))
        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        _, task_idx = _decode(index.internalId())
        if task_idx == -1:
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
