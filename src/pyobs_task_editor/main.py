import sys
from PySide6 import QtWidgets
from qt_material import apply_stylesheet

from .mainwindow import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme="dark_blue.xml")
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
