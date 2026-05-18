from PySide6 import QtWidgets, QtCore
from pyobs.robotic import Task, ObservationList

from pyobs_task_editor.backends import Backend


class ObservationListWidget(QtWidgets.QTableWidget):
    def __init__(self):
        super().__init__()

        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["ID", "Start", "End", "Duration", "State"])
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

    def set_backend(self, backend: Backend):
        self._backend = backend

    @QtCore.Slot(ObservationList)
    def set_observations(self, observations: ObservationList) -> None:
        self.setRowCount(len(observations))
        for row, obs in enumerate(observations):
            total_seconds = int((obs.end - obs.start).sec)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            self.setItem(row, 0, QtWidgets.QTableWidgetItem(str(obs.id)))
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(obs.start.strftime("%Y-%m-%d %H:%M:%S")))
            self.setItem(row, 2, QtWidgets.QTableWidgetItem(obs.end.strftime("%Y-%m-%d %H:%M:%S")))
            self.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{hours:02}:{minutes:02}:{seconds:02}"))
            self.setItem(row, 4, QtWidgets.QTableWidgetItem(str(obs.state)))
        self.resizeColumnsToContents()
        self.horizontalHeader().setStretchLastSection(True)
