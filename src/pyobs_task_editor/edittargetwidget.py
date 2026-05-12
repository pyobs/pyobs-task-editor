from astropy.coordinates import SkyCoord
from PySide6 import QtWidgets, QtCore

from pyobs.robotic import Task
from pyobs.robotic.scheduler.targets import Target, SiderealTarget


class EditTargetWidget(QtWidgets.QWidget):
    target_changed = QtCore.Signal(Target)

    def __init__(self):
        super().__init__()

        self._task: Task | None = None
        self._updating = False

        self.setLayout(QtWidgets.QVBoxLayout())
        group = QtWidgets.QGroupBox("Target")
        self.layout().addWidget(group)

        self.form_layout = QtWidgets.QFormLayout()
        group.setLayout(self.form_layout)

        self.target_type = QtWidgets.QComboBox()
        self.target_type.setEditable(False)
        self.target_type.addItems(["None", "Sidereal"])
        self.target_type.currentTextChanged.connect(self._type_changed)
        self.form_layout.addRow("Type", self.target_type)

        self.target_name: QtWidgets.QLineEdit | None = None

    @QtCore.Slot(Task)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task

        if task is None or task.target is None:
            self.target_type.setCurrentText("None")

        elif isinstance(task.target, SiderealTarget):
            self.target_type.setCurrentText("Sidereal")
            self.target_name.setText(task.target.name)
            coords = SkyCoord(ra=task.target.ra, dec=task.target.dec, frame="icrs", unit="deg")
            self.ra.setText(coords.ra.to_string(sep=" ", pad=True))
            self.dec.setText(coords.dec.to_string(sep=" ", pad=True, alwayssign=True))

        self._updating = False

    @QtCore.Slot()
    def _update_sidereal_target(self):
        if self._updating or self._task is None:
            return

        target = self._task.target
        target.name = self.target_name.text()
        try:
            coord = SkyCoord(ra=self.ra.text(), dec=self.dec.text(), frame="icrs", unit="deg")
            target.ra = float(coord.ra.degree)
            target.dec = float(coord.dec.degree)
        except ValueError:
            target.ra = 0.0
            target.dec = 0.0

        if not self._updating:
            self.target_changed.emit(target)

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def _type_changed(self, typ: str) -> None:
        for i in reversed(range(1, self.form_layout.rowCount())):
            self.form_layout.removeRow(i)

        if typ != "None":
            self.target_name = QtWidgets.QLineEdit()
            self.target_name.textChanged.connect(self._update_sidereal_target)
            self.form_layout.addRow("Name", self.target_name)

        if typ == "None":
            self._task.target = None
        if typ == "Sidereal":
            if not isinstance(self._task.target, SiderealTarget):
                self._task.target = SiderealTarget(name="unknown", ra=0, dec=0)
            self.ra = QtWidgets.QLineEdit()
            self.ra.textChanged.connect(self._update_sidereal_target)
            self.form_layout.addRow("RA", self.ra)
            self.dec = QtWidgets.QLineEdit()
            self.dec.textChanged.connect(self._update_sidereal_target)
            self.form_layout.addRow("Dec", self.dec)

        if not self._updating:
            self.target_changed.emit(self._task.target)
