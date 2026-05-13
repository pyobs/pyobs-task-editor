from urllib.parse import urljoin
import requests
from PySide6 import QtWidgets, QtCore

from pyobs_task_editor.listwithbuttonswidget import ListWithButtonsWidget


class ConnectionsDialog(QtWidgets.QDialog):
    def __init__(self, config) -> None:
        super().__init__()
        self.resize(600, 300)
        self.setWindowTitle("Connections")

        self.config = config
        self.updating = False

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        hlayout = QtWidgets.QHBoxLayout()
        layout.addLayout(hlayout)

        self.list_widget = ListWithButtonsWidget()
        self.list_widget.item_selected.connect(self._connection_selected)
        self.list_widget.add_clicked.connect(self._add_connection)
        self.list_widget.remove_clicked.connect(self._remove_connection)
        hlayout.addWidget(self.list_widget)
        hlayout.addWidget(self.list_widget)

        self.group_connection = QtWidgets.QGroupBox()
        connection_layout = QtWidgets.QFormLayout()
        self.group_connection.setLayout(connection_layout)
        hlayout.addWidget(self.group_connection)

        self.name_widget = QtWidgets.QLineEdit()
        self.name_widget.textChanged.connect(self._update_connection_from_gui)
        connection_layout.addRow("Name", self.name_widget)
        self.url_widget = QtWidgets.QLineEdit()
        self.url_widget.textChanged.connect(self._update_connection_from_gui)
        connection_layout.addRow("URL", self.url_widget)
        self.token_widget = QtWidgets.QLineEdit()
        self.token_widget.textChanged.connect(self._update_connection_from_gui)
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
        self.login_button.clicked.connect(self._login)
        login_layout.addWidget(self.login_button)

        buttons = QtWidgets.QDialogButtonBox()
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_connection_list()

    @QtCore.Slot()
    def _login(self) -> None:
        res = requests.post(
            urljoin(self.url_widget.text(), "/api-token-auth/"),
            json={"username": self.username_widget.text(), "password": self.password_widget.text()},
        ).json()
        if "token" in res:
            self.token_widget.setText(res["token"])
            self.username_widget.clear()
            self.password_widget.clear()

    @QtCore.Slot()
    def _connection_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            self.name_widget.clear()
            self.url_widget.clear()
            self.token_widget.clear()
            return
        self.updating = True
        conn = item.data(QtCore.Qt.UserRole)
        self.name_widget.setText(conn.name)
        self.url_widget.setText(conn.url)
        self.token_widget.setText(conn.token)
        self.updating = False

    @QtCore.Slot()
    def _add_connection(self) -> None:
        from .mainwindow import Connection

        self.config.connections.append(Connection(name="new connection", url="", token=""))
        self.update_connection_list()

    @QtCore.Slot()
    def _remove_connection(self) -> None:
        pass

    @QtCore.Slot()
    def _update_connection_from_gui(self) -> None:
        item = self.list_widget.currentItem()
        if self.updating or item is None:
            return
        conn = item.data(QtCore.Qt.UserRole)
        conn.name = self.name_widget.text()
        conn.url = self.url_widget.text()
        conn.token = self.token_widget.text()

    @QtCore.Slot(str)
    def update_connection_list(self, selected: str | None = None) -> None:
        self.list_widget.clear()
        row = 0
        for i, conn in enumerate(self.config.connections):
            item = QtWidgets.QListWidgetItem(conn.name)
            item.setData(QtCore.Qt.UserRole, conn)
            self.list_widget.addItem(item)
            if conn.name == selected:
                row = i
        self.list_widget.setCurrentRow(row)
