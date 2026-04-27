import sys
import os

# Ensure the project root is on the path regardless of launch directory
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import pyqtgraph as pg

from ui.main_window import MainWindow


def main():
    pg.setConfigOptions(antialias=True, useOpenGL=True)

    app = QApplication(sys.argv)
    app.setApplicationName("Swarm Minimizer")
    app.setOrganizationName("VKR")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
