from PySide6 import QtWidgets, QtCore

from pyobs.robotic import Task
from pyobs_task_editor.backends import HttpBackend
from pyobs_task_editor.tasklistwidget import TaskListWidget
from pyobs_task_editor.taskwidget import TaskWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(800, 600)
        self.setWindowTitle("pyobs task editor")

        splitter = QtWidgets.QSplitter()
        self.setCentralWidget(splitter)

        self.task_list = TaskListWidget()
        splitter.addWidget(self.task_list)

        self.task_widget = TaskWidget()
        splitter.addWidget(self.task_widget)

        splitter.setSizes([1, 3])

        self.task_list.task_selected.connect(self.task_widget.set_task)

        self.backend = HttpBackend()
        self.update_task_list()

    def update_task_list(self):
        tasks = self.backend.get_tasks()
        self.task_list.set_tasks(tasks)
