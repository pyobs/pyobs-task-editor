from PySide6 import QtWidgets, QtCore
import qtawesome as qa

from pyobs_task_editor.backends import Backend, User


class UsersDialog(QtWidgets.QDialog):
    def __init__(self, backend: Backend) -> None:
        super().__init__()
        self.resize(600, 300)
        self.setWindowTitle("Users")

        self._backend = backend
        self._users = backend.get_users()
        self._updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Admin", "Username", "Email"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        hlayout = QtWidgets.QHBoxLayout()
        layout.addLayout(hlayout)

        add_user = QtWidgets.QPushButton("Add User")
        add_user.setIcon(qa.icon("fa5s.plus"))
        add_user.clicked.connect(self._add_user)
        hlayout.addWidget(add_user)

        buttons = QtWidgets.QDialogButtonBox()
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._close)
        buttons.rejected.connect(self.close)
        hlayout.addWidget(buttons)

        self._fill_table()

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self._users))
        for i, user in enumerate(self._users):
            self._fill_table_row(i, user)

    def _fill_table_row(self, row: int, user: User) -> None:
        user_id = QtWidgets.QTableWidgetItem(str(user.id))
        user_id.setData(QtCore.Qt.ItemDataRole.UserRole, user)
        self.table.setItem(row, 0, user_id)
        admin = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        admin.setLayout(layout)
        is_admin = QtWidgets.QCheckBox()
        is_admin.setChecked(user.is_superuser)
        is_admin.checkStateChanged.connect(lambda c: self._update_admin(user, c == QtCore.Qt.CheckState.Checked))
        layout.addWidget(is_admin)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 1, admin)
        username = QtWidgets.QTableWidgetItem(user.username)
        self.table.setItem(row, 2, username)
        email = QtWidgets.QLineEdit(user.email)
        email.textChanged.connect(lambda c: self._update_email(user, c))
        self.table.setCellWidget(row, 3, email)

        self.table.resizeColumnToContents(1)

    def _update_admin(self, user: User, is_admin: bool) -> None:
        user.is_superuser = is_admin

    def _update_email(self, user: User, email: str) -> None:
        user.email = email

    @QtCore.Slot()
    def _add_user(self) -> None:
        username, ok = QtWidgets.QInputDialog.getText(self, "New user", "Username for new user")
        if not ok:
            return

        user = User(username=username)
        self._users.append(user)
        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        self._fill_table_row(row, user)

    @QtCore.Slot()
    def _close(self):
        for row in range(self.table.rowCount()):
            user = self.table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole)
            if user.id is None:
                self._backend.add_user(user)
            else:
                self._backend.update_user(user)
        self.accept()
