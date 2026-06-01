from astropy.coordinates import SkyCoord
from PySide6 import QtWidgets, QtCore
import astropy.units as u

from pyobs.robotic import Task
from pyobs.robotic.scheduler.targets import Target, SiderealTarget

try:
    from pyobs.robotic.scheduler.targets.dynamictarget import DynamicTarget
    from pyobs.robotic.scheduler.targets.picker import CsvPicker

    HAS_DYNAMIC_TARGET = True
except ImportError:
    HAS_DYNAMIC_TARGET = False

if HAS_DYNAMIC_TARGET:
    from pyobs_task_editor.editpickerwidget import EditPickerWidget


class EditTargetWidget(QtWidgets.QWidget):
    target_changed = QtCore.Signal(Target)
    task_changed = QtCore.Signal(Task)

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
        types = ["None", "Sidereal"]
        if HAS_DYNAMIC_TARGET:
            types.append("Dynamic")
        self.target_type.addItems(types)
        self.target_type.currentTextChanged.connect(self._type_changed)
        self.form_layout.addRow("Type", self.target_type)

        self.target_name: QtWidgets.QLineEdit | None = None
        self.ra: QtWidgets.QLineEdit | None = None
        self.dec: QtWidgets.QLineEdit | None = None
        self.picker_widget: EditPickerWidget | None = None

    @QtCore.Slot(Task)
    def set_task(self, task: Task) -> None:
        self._updating = True
        self._task = task

        if task is None or task.target is None:
            self.target_type.setCurrentText("None")
            self._rebuild_fields("None")

        elif HAS_DYNAMIC_TARGET and isinstance(task.target, DynamicTarget):
            self.target_type.setCurrentText("Dynamic")
            self._rebuild_fields("Dynamic")
            self.picker_widget.set_picker(task.target.picker)

        elif isinstance(task.target, SiderealTarget):
            self.target_type.setCurrentText("Sidereal")
            self._rebuild_fields("Sidereal")
            self.target_name.setText(task.target.name)
            coords = SkyCoord(ra=task.target.ra, dec=task.target.dec, frame="icrs", unit="deg")
            self.ra.setText(coords.ra.to_string(sep=" ", pad=True, unit="hourangle"))
            self.dec.setText(coords.dec.to_string(sep=" ", pad=True, alwayssign=True))

        self._updating = False

    def _rebuild_fields(self, typ: str):
        """Rebuild form rows below the Type combobox for the given type."""
        for i in reversed(range(1, self.form_layout.rowCount())):
            self.form_layout.removeRow(i)

        self.target_name = None
        self.ra = None
        self.dec = None
        self.picker_widget = None

        if typ == "Sidereal":
            self.target_name = QtWidgets.QLineEdit()
            self.target_name.textChanged.connect(self._update_sidereal_target)
            self.form_layout.addRow("Name", self.target_name)
            self.ra = QtWidgets.QLineEdit()
            self.ra.textChanged.connect(self._update_sidereal_target)
            self.form_layout.addRow("RA", self.ra)
            self.dec = QtWidgets.QLineEdit()
            self.dec.textChanged.connect(self._update_sidereal_target)
            self.form_layout.addRow("Dec", self.dec)

        elif typ == "Dynamic" and HAS_DYNAMIC_TARGET:
            self.picker_widget = EditPickerWidget()
            self.picker_widget.picker_changed.connect(self._update_dynamic_target)
            self.form_layout.addRow(self.picker_widget)

    @QtCore.Slot(str)
    def _type_changed(self, typ: str) -> None:
        if self._task is None:
            return

        self._rebuild_fields(typ)

        if typ == "None":
            self._task.target = None
        elif typ == "Sidereal":
            if not isinstance(self._task.target, SiderealTarget):
                self._task.target = SiderealTarget(name="unknown", ra=0, dec=0)
            self.target_name.setText(self._task.target.name)
            coords = SkyCoord(ra=self._task.target.ra, dec=self._task.target.dec, frame="icrs", unit="deg")
            self.ra.setText(coords.ra.to_string(sep=" ", pad=True, unit="hourangle"))
            self.dec.setText(coords.dec.to_string(sep=" ", pad=True, alwayssign=True))
        elif typ == "Dynamic" and HAS_DYNAMIC_TARGET:
            if not isinstance(self._task.target, DynamicTarget):
                self._task.target = DynamicTarget(picker=CsvPicker(csv="targets.csv"))
            self.picker_widget.set_picker(self._task.target.picker)

        if not self._updating:
            self.target_changed.emit(self._task.target)
            self.task_changed.emit(self._task)

    @QtCore.Slot()
    def _update_sidereal_target(self):
        if self._updating or self._task is None:
            return

        target = self._task.target
        target.name = self.target_name.text()
        try:
            coord = SkyCoord(ra=self.ra.text(), dec=self.dec.text(), unit=(u.hourangle, u.deg), frame="icrs")
            target.ra = float(coord.ra.degree)
            target.dec = float(coord.dec.degree)
        except ValueError:
            target.ra = 0.0
            target.dec = 0.0

        self.target_changed.emit(target)
        self.task_changed.emit(self._task)

    @QtCore.Slot(object)
    def _update_dynamic_target(self, picker):
        if self._updating or self._task is None:
            return
        self._task.target.picker = picker
        self.target_changed.emit(self._task.target)
        self.task_changed.emit(self._task)
