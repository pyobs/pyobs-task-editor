from astropy.coordinates import SkyCoord
from typing import cast
from PySide6 import QtWidgets, QtCore
from pyobs.robotic.scheduler.targets import Target, SiderealTarget

from pyobs_task_editor.backends import Backend


class EditTargetWidget(QtWidgets.QGroupBox):
    target_changed = QtCore.Signal(Target)

    def __init__(self, backend: Backend):
        super().__init__()

        self.target: Target | None = None
        self._updating = False

        self.setTitle("Target")
        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.target_type = QtWidgets.QComboBox()
        self.target_type.setEditable(False)
        self.target_type.addItems(["None", "Sidereal"])
        self.target_type.currentTextChanged.connect(self._type_changed)
        layout.addRow("Type", self.target_type)

    @QtCore.Slot(Target)
    def set_target(self, target: Target) -> None:
        self._updating = True
        self.target = target

        if target is None:
            self.target_type.setCurrentText("None")

        elif isinstance(target, SiderealTarget):
            self.target_type.setCurrentText("Sidereal")
            self.target_name.setText(target.name)
            coords = SkyCoord(ra=target.ra, dec=target.dec, frame="icrs", unit="deg")
            self.ra.setText(coords.ra.to_string(sep=" ", pad=True))
            self.dec.setText(coords.dec.to_string(sep=" ", pad=True, alwayssign=True))

        self._updating = False

    @QtCore.Slot()
    def _update_sidereal_target(self):
        self.target.name = self.target_name.text()
        try:
            coord = SkyCoord(ra=self.ra.text(), dec=self.dec.text(), frame="icrs", unit="deg")
            self.target.ra = float(coord.ra.degree)
            self.target.dec = float(coord.dec.degree)
        except ValueError:
            self.target.ra = 0.0
            self.target.dec = 0.0

        if not self._updating:
            self.target_changed.emit(self.target)

    @QtCore.Slot(str)
    @QtCore.Slot(str)
    def _type_changed(self, typ: str) -> None:
        layout = cast(QtWidgets.QFormLayout, self.layout())
        for i in reversed(range(1, layout.rowCount())):
            layout.removeRow(i)

        if typ != "None":
            self.target_name = QtWidgets.QLineEdit()
            self.target_name.textChanged.connect(self._update_sidereal_target)
            layout.addRow("Name", self.target_name)

        if typ == "None":
            self.target = None
        if typ == "Sidereal":
            self.target = SiderealTarget(name="unknown", ra=0, dec=0)
            self.ra = QtWidgets.QLineEdit()
            self.ra.textChanged.connect(self._update_sidereal_target)
            layout.addRow("RA", self.ra)
            self.dec = QtWidgets.QLineEdit()
            self.dec.textChanged.connect(self._update_sidereal_target)
            layout.addRow("Dec", self.dec)

        if not self._updating:
            self.target_changed.emit(self.target)
