from PySide6 import QtWidgets, QtCore

from pyobs_task_editor.backends import Backend, Project
from pyobs_task_editor.listwithbuttonswidget import ListWithButtonsWidget


class ProjectsDialog(QtWidgets.QDialog):
    def __init__(self, backend: Backend) -> None:
        super().__init__()
        self.resize(600, 300)
        self.setWindowTitle("Projects")

        self._backend = backend
        self._projects = backend.get_projects()
        projects = [p.code for p in backend.get_projects()]
        self._current_project: Project | None = None
        self._updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        hlayout = QtWidgets.QHBoxLayout()
        layout.addLayout(hlayout)

        self.list_widget = ListWithButtonsWidget()
        self.list_widget.addItems(projects)
        self.list_widget.item_selected.connect(self._project_selected)
        self.list_widget.add_clicked.connect(self._add_project)
        self.list_widget.remove_clicked.connect(self._remove_project)
        hlayout.addWidget(self.list_widget)

        self.group_project = QtWidgets.QGroupBox()
        project_layout = QtWidgets.QFormLayout()
        self.group_project.setLayout(project_layout)
        hlayout.addWidget(self.group_project)

        self.project_id = QtWidgets.QLineEdit()
        self.project_id.setReadOnly(True)
        project_layout.addRow("ID", self.project_id)
        self.project_name = QtWidgets.QLineEdit()
        self.project_name.textChanged.connect(self._update_project_from_gui)
        project_layout.addRow("Name", self.project_name)
        self.priority = QtWidgets.QDoubleSpinBox()
        self.priority.valueChanged.connect(self._update_project_from_gui)
        project_layout.addRow("Priority", self.priority)

        buttons = QtWidgets.QDialogButtonBox()
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

    @QtCore.Slot()
    def _update_project_from_gui(self) -> None:
        if self._current_project is None or self._updating:
            return
        self._current_project.name = str(self.project_name.text())
        self._current_project.priority = self.priority.value()

    @QtCore.Slot()
    def _add_project(self) -> None:
        code, ok = QtWidgets.QInputDialog.getText(self, "New Task", "ID of new Task")
        if ok:
            self._projects.append(Project(code=code, name=str(code)))
            self.list_widget.addItem(code)

    @QtCore.Slot()
    def _remove_project(self) -> None:
        if self._current_project is None:
            return
        tasks = self._backend.get_tasks(self._current_project)
        if len(tasks) > 0:
            QtWidgets.QMessageBox.warning(self, "Warning", "Can not delete project, since it contains tasks.")
            return
        if (
            QtWidgets.QMessageBox.question(
                self, "Delete project", f"Really delete project {self._current_project.code}?"
            )
            == QtWidgets.QMessageBox.accepted
        ):
            pass

    @QtCore.Slot()
    def _project_selected(self, code: str):
        if code == "":
            self._current_project = None
        else:
            for p in self._projects:
                if p.code == code:
                    self._current_project = p
                    break
            else:
                self._current_project = None

        self.group_project.setEnabled(self._current_project is not None)
        if self._current_project is None:
            self.project_id.clear()
            self.project_name.clear()
            self.priority.setValue(0)
        else:
            self._updating = True
            self.project_id.setText(str(self._current_project.code))
            self.project_name.setText(str(self._current_project.name))
            self.priority.setValue(self._current_project.priority)
            self._updating = False

    @QtCore.Slot()
    def _close(self):
        existing_projects = [p.code for p in self._backend.get_projects()]
        for project in self._projects:
            if project.code in existing_projects:
                self._backend.update_project(project)
            else:
                self._backend.add_project(project)
        self.accept()
