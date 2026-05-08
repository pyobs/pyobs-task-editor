from PySide6 import QtWidgets, QtCore, QtGui
import qtawesome as qa

from pyobs.robotic import Task
from pyobs_task_editor.backends import HttpBackend
from pyobs_task_editor.tasklistwidget import TaskListWidget
from pyobs_task_editor.taskwidget import TaskWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(800, 600)
        self.setWindowTitle("pyobs task editor")

        toolbar = QtWidgets.QToolBar("Main ToolBar")
        self.addToolBar(toolbar)

        self.action_connection = QtGui.QAction(qa.icon("mdi6.cast-connected"), "New", self)
        toolbar.addAction(self.action_connection)
        toolbar.addSeparator()
        self.action_new = QtGui.QAction(qa.icon("mdi6.file-document-plus-outline"), "New", self)
        self.action_new.triggered.connect(self._new_task)
        toolbar.addAction(self.action_new)
        self.action_save = QtGui.QAction(qa.icon("mdi6.content-save-edit-outline"), "Save", self)
        self.action_save.triggered.connect(self._save_task)
        toolbar.addAction(self.action_save)
        self.action_sync = QtGui.QAction(qa.icon("mdi6.sync"), "Sync", self)
        toolbar.addAction(self.action_sync)
        self.action_sync.triggered.connect(self._sync_tasks)

        splitter = QtWidgets.QSplitter()
        self.setCentralWidget(splitter)

        self.task_list = TaskListWidget()
        splitter.addWidget(self.task_list)

        self.task_widget = TaskWidget()
        splitter.addWidget(self.task_widget)

        splitter.setSizes([1, 3])

        self.task_list.task_selected.connect(self.task_widget.set_task)

        self.backend = HttpBackend()
        self._sync_tasks()

    @QtCore.Slot()
    def _new_task(self):
        self.task_list.add_task(Task(id="newtask", name="New task"))

    @QtCore.Slot()
    def _save_task(self):
        pass

    @QtCore.Slot()
    def _sync_tasks(self):
        tasks = self.backend.get_tasks()
        self.task_list.set_tasks(tasks)
