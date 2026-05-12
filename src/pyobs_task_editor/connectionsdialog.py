from PySide6 import QtWidgets, QtCore

from pyobs_task_editor.backends import Backend, Project, User
from pyobs_task_editor.listwithbuttonswidget import ListWithButtonsWidget


class ConnectionsDialog(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.resize(600, 300)
        self.setWindowTitle("Connections")

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        hlayout = QtWidgets.QHBoxLayout()
        layout.addLayout(hlayout)

        self.list_widget = ListWithButtonsWidget()
        # self.list_widget.addItems(projects)
        self.list_widget.item_selected.connect(self._project_selected)
        self.list_widget.add_clicked.connect(self._add_project)
        self.list_widget.remove_clicked.connect(self._remove_project)
        hlayout.addWidget(self.list_widget)

        self.group_connection = QtWidgets.QGroupBox()
        connection_layout = QtWidgets.QFormLayout()
        self.group_connection.setLayout(connection_layout)
        hlayout.addWidget(self.group_connection)

        self.name_widget = QtWidgets.QLineEdit()
        self.name_widget.textChanged.connect(self._update_project_from_gui)
        connection_layout.addRow("Name", self.name_widget)
        self.url_widget = QtWidgets.QLineEdit()
        self.url_widget.textChanged.connect(self._update_project_from_gui)
        connection_layout.addRow("URL", self.url_widget)
        self.token_widget = QtWidgets.QLineEdit()
        self.token_widget.textChanged.connect(self._update_project_from_gui)
        connection_layout.addRow("Token", self.token_widget)

        group_login = QtWidgets.QGroupBox("Get token")
        connection_layout.addWidget(group_login)
        login_layout = QtWidgets.QFormLayout()
        group_login.setLayout(login_layout)

        self.username_widget = QtWidgets.QLineEdit()
        login_layout.addRow("Username", self.username_widget)
        self.password_widget = QtWidgets.QLineEdit()
        self.password_widget.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        login_layout.addRow("Password", self.password_widget)
        self.login_button = QtWidgets.QPushButton("Login")
        login_layout.addWidget(self.login_button)

        buttons = QtWidgets.QDialogButtonBox()
        buttons.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @QtCore.Slot()
    def _update_project_from_gui(self) -> None:
        if self._current_project is None or self._updating:
            return
        self._current_project.name = str(self.project_name.text())
        self._current_project.priority = self.priority.value()
        self._current_project.users = [
            self.users.item(i).text()
            for i in range(self.users.count())
            if self.users.item(i).checkState() == QtCore.Qt.CheckState.Checked
        ]

    @QtCore.Slot()
    def _add_project(self) -> None:
        code, ok = QtWidgets.QInputDialog.getText(self, "New Task", "ID of new Task")
        if ok:
            self._projects.append(Project(code=code, name=str(code), priority=1.0))
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

        self.group_connection.setEnabled(self._current_project is not None)
        if self._current_project is None:
            self.project_id.clear()
            self.project_name.clear()
            self.priority.setValue(0)
        else:
            self._updating = True
            self.project_id.setText(str(self._current_project.code))
            self.project_name.setText(str(self._current_project.name))
            self.priority.setValue(self._current_project.priority)
            self.users.clear()
            for user in self._backend.get_users():
                item = QtWidgets.QListWidgetItem(user.username)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, user)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    QtCore.Qt.CheckState.Checked
                    if user.username in self._current_project.users
                    else QtCore.Qt.CheckState.Unchecked
                )
                self.users.addItem(item)

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
