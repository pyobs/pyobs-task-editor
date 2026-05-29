import functools
import pydantic
import yaml
from PySide6 import QtWidgets, QtCore, QtGui
import qtawesome as qa
from platformdirs import PlatformDirs
from pydantic import Field

from pyobs.robotic import Task
from pyobs_task_editor.backends import HttpBackend, Backend, User
from pyobs_task_editor.connectionsdialog import ConnectionsDialog
from pyobs_task_editor.projectsdialog import ProjectsDialog
from pyobs_task_editor.tasklistwidget import TaskListWidget
from pyobs_task_editor.tasktreemodel import TaskTreeModel
from pyobs_task_editor.taskwidget import TaskWidget
from pyobs_task_editor.usersdialog import UsersDialog


class Connection(pydantic.BaseModel):
    name: str
    url: str
    token: str


class Config(pydantic.BaseModel):
    connections: list[Connection] = Field(default_factory=list)


class SyncTasksThread(QtCore.QThread):
    tasks_ready = QtCore.Signal(list)

    def __init__(self, parent, backend: Backend):
        QtCore.QThread.__init__(self, parent)
        self.backend = backend

    def run(self) -> None:
        tasks = self.backend.get_tasks()
        self.tasks_ready.emit(tasks)


class SaveTaskThread(QtCore.QThread):
    task_saved = QtCore.Signal()

    def __init__(self, parent, backend: Backend, task: Task):
        QtCore.QThread.__init__(self, parent)
        self.backend = backend
        self.task = task

    def run(self) -> None:
        all_tasks = self.backend.get_tasks()
        existing_task = any([t.id == self.task.id for t in all_tasks])
        if existing_task:
            self.backend.update_task(self.task)
        else:
            self.backend.add_task(self.task)

        self.task_saved.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.config = Config()
        self._read_config()
        self.backend: Backend | None = None
        self._user: User | None = None

        self.resize(800, 600)
        self.setWindowTitle("pyobs task editor")

        toolbar = QtWidgets.QToolBar("Main ToolBar")
        self.addToolBar(toolbar)

        self.connection_menu = QtWidgets.QMenu()
        for conn in self.config.connections:
            action = QtGui.QAction(conn.name, self)
            action.triggered.connect(functools.partial(self._connect, conn))
            self.connection_menu.addAction(action)

        self.connection_widget = QtWidgets.QToolButton()
        self.connection_widget.setIcon(qa.icon("mdi6.cast-connected"))
        self.connection_widget.setToolTip("Connections")
        self.connection_widget.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.connection_widget.setMenu(self.connection_menu)
        self.connection_widget.clicked.connect(self._edit_connections)
        toolbar.addWidget(self.connection_widget)

        toolbar.addSeparator()
        self.action_new = QtGui.QAction(qa.icon("mdi6.file-document-plus-outline"), "New", self)
        self.action_new.triggered.connect(self._new_task)
        toolbar.addAction(self.action_new)
        self.action_save = QtGui.QAction(qa.icon("mdi6.content-save-edit-outline"), "Save", self)
        self.action_save.triggered.connect(self._save_task)
        toolbar.addAction(self.action_save)
        self.action_export = QtGui.QAction(qa.icon("mdi6.database-export-outline"), "Export", self)
        self.action_export.triggered.connect(self._export_task)
        toolbar.addAction(self.action_export)
        self.action_sync = QtGui.QAction(qa.icon("mdi6.sync"), "Sync", self)
        toolbar.addAction(self.action_sync)
        self.action_sync.triggered.connect(self.sync_tasks)
        toolbar.addSeparator()
        self.action_projects = QtGui.QAction(qa.icon("mdi6.format-list-group"), "Projects", self)
        self.action_projects.triggered.connect(self._edit_projects)
        toolbar.addAction(self.action_projects)
        self.action_users = QtGui.QAction(qa.icon("mdi6.account-group"), "Users", self)
        self.action_users.triggered.connect(self._edit_users)
        toolbar.addAction(self.action_users)

        splitter = QtWidgets.QSplitter()
        self.setCentralWidget(splitter)

        self.model = TaskTreeModel()
        self.task_list = TaskListWidget()
        self.task_list.set_model(self.model)
        splitter.addWidget(self.task_list)

        self.task_widget = TaskWidget(self.backend)
        splitter.addWidget(self.task_widget)

        splitter.setSizes([1, 3])
        self.task_list.task_selected.connect(self.task_widget.set_task)

        self._update_enabled()

    def _read_config(self):
        dirs = PlatformDirs("pyobs-task-editor", "pyobs")
        try:
            with open(dirs.user_config_path, "r") as f:
                self.config = Config.model_validate(yaml.safe_load(f))
        except FileNotFoundError:
            self.config = Config()

    def _write_config(self):
        dirs = PlatformDirs("pyobs-task-editor", "pyobs")
        with open(dirs.user_config_path, "w") as f:
            yaml.safe_dump(self.config.model_dump(), f)

    @QtCore.Slot()
    def _new_task(self):
        code, ok = QtWidgets.QInputDialog.getText(self, "New Task", "ID of new Task")
        if ok:
            self.task_list.add_task(Task(id=code, name=code))

    @QtCore.Slot()
    def _save_task(self):
        task = self.task_widget.get_task()
        if task is None:
            return

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        thread = SaveTaskThread(self, self.backend, task)
        thread.task_saved.connect(QtWidgets.QApplication.restoreOverrideCursor)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    @QtCore.Slot()
    def _export_task(self):
        task = self.task_widget.get_task()
        if task is None:
            return

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("YAML")
        dlg.resize(600, 400)

        layout = QtWidgets.QVBoxLayout(dlg)

        text = QtWidgets.QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(yaml.dump(task.model_dump()))
        layout.addWidget(text)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        dlg.exec()

    @QtCore.Slot()
    def sync_tasks(self):
        if (
            QtWidgets.QMessageBox.question(self, "Sync tasks", "Syncing tasks will undo all local changes. Continue?")
            == QtWidgets.QMessageBox.StandardButton.Yes
        ):
            self._sync_tasks()

    @QtCore.Slot()
    def _sync_tasks(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        thread = SyncTasksThread(self, self.backend)
        thread.tasks_ready.connect(self._tasks_synced)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    @QtCore.Slot(list)
    def _tasks_synced(self, tasks: list[Task]):
        QtWidgets.QApplication.restoreOverrideCursor()
        self.task_list.set_tasks(tasks)

    @QtCore.Slot()
    def _edit_projects(self):
        dialog = ProjectsDialog(self.backend)
        dialog.exec_()

    @QtCore.Slot()
    def _edit_users(self):
        dialog = UsersDialog(self.backend)
        dialog.exec_()

    @QtCore.Slot()
    def _edit_connections(self):
        dialog = ConnectionsDialog(self.config.model_copy())
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.config = dialog.config
            self._write_config()

    @QtCore.Slot(Connection)
    def _connect(self, conn):
        self.backend = HttpBackend(url=conn.url, token=conn.token)
        self._user = self.backend.connect()
        self.task_widget.set_backend(self.backend)
        self._update_enabled()
        self._sync_tasks()

    @QtCore.Slot()
    def _update_enabled(self):
        has_backend = self.backend is not None
        is_superuser = self._user is not None and self._user.is_superuser
        self.task_list.setEnabled(has_backend)
        self.task_widget.setEnabled(has_backend)
        self.action_new.setEnabled(has_backend)
        self.action_save.setEnabled(has_backend)
        self.action_export.setEnabled(has_backend)
        self.action_sync.setEnabled(has_backend)
        self.action_projects.setEnabled(has_backend and is_superuser)
        self.action_users.setEnabled(has_backend and is_superuser)
