import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

from core import Evaluator, FunctionParser, FunctionRegistry
from export import CsvExporter, PngExporter

from .algorithm_panel import AlgorithmPanel
from .controller import Controller
from .function_panel import FunctionPanel
from .plot_2d import Plot2DWidget
from .plot_3d import Plot3DWidget


def _make_stylesheet() -> str:
    up = os.path.join(_ASSETS, "arrow_up.svg").replace("\\", "/")
    dn = os.path.join(_ASSETS, "arrow_down.svg").replace("\\", "/")
    return _STYLESHEET_TEMPLATE.replace("__UP__", up).replace("__DN__", dn)


_STYLESHEET_TEMPLATE = """
QMainWindow { background: #1e1e2e; }
QWidget { background: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 8px;
    padding: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #89b4fa;
    font-weight: bold;
}
QPushButton {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 4px 10px;
    color: #cdd6f4;
}
QPushButton:hover { background: #45475a; }
QPushButton:pressed { background: #585b70; }
QPushButton#remove_btn {
    background: transparent;
    border: none;
    color: #f38ba8;
    font-size: 11px;
}
QPushButton#remove_btn:hover { color: #ff6c7b; }
QLineEdit {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QLineEdit:focus { border-color: #89b4fa; }
QComboBox {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 3px 8px;
    color: #cdd6f4;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #313244; color: #cdd6f4; }
QSpinBox, QDoubleSpinBox {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 2px 22px 2px 6px;
    color: #cdd6f4;
    min-height: 22px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #585b70;
    border-top-right-radius: 3px;
    background: #45475a;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #585b70;
    border-bottom-right-radius: 3px;
    background: #45475a;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #585b70;
}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background: #6c6f85;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url("__UP__");
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url("__DN__");
    width: 10px;
    height: 6px;
}
QProgressBar {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    height: 14px;
}
QProgressBar::chunk { background: #89b4fa; border-radius: 3px; }
QSlider::groove:horizontal {
    background: #313244;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #89b4fa;
    width: 14px; height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #89b4fa; border-radius: 3px; }
QRadioButton::indicator { width: 14px; height: 14px; }
QScrollArea { border: none; }
QStatusBar { background: #181825; color: #a6adc8; font-size: 12px; }
QToolBar { background: #181825; border: none; spacing: 4px; }
QToolBar QToolButton {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QToolBar QToolButton:hover { background: #45475a; }
QLabel#hint_label { color: #6c7086; font-size: 11px; }
QLabel#result_label {
    color: #a6e3a1;
    font-family: monospace;
    padding: 4px;
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 4px;
}
QListWidget { background: #181825; border: 1px solid #313244; border-radius: 4px; }
QListWidget::item { padding: 2px; }
QListWidget::item:selected { background: #313244; }
QSplitter::handle { background: #45475a; width: 2px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stimaf — Алгоритмы роевого интеллекта")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(_make_stylesheet())

        self._build_ui()
        self._build_controller()
        self._build_toolbar()
        self._build_statusbar()

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        # Left: plot area (2D / 3D stacked)
        self._plot_stack = QStackedWidget()
        self._plot_2d = Plot2DWidget()
        self._plot_3d = Plot3DWidget()
        self._plot_stack.addWidget(self._plot_2d)  # index 0
        self._plot_stack.addWidget(self._plot_3d)  # index 1
        splitter.addWidget(self._plot_stack)

        # Right: control panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        control_container = QWidget()
        control_layout = QVBoxLayout(control_container)
        control_layout.setContentsMargins(6, 6, 6, 6)
        control_layout.setSpacing(6)

        self._func_panel = FunctionPanel()
        self._algo_panel = AlgorithmPanel()

        control_layout.addWidget(self._func_panel)
        control_layout.addWidget(self._algo_panel)
        control_layout.addStretch()

        scroll.setWidget(control_container)
        right_layout.addWidget(scroll)
        splitter.addWidget(right_widget)

        splitter.setSizes([820, 380])
        self.setCentralWidget(splitter)

    def _build_toolbar(self):
        toolbar = QToolBar("Инструменты")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_png = QAction("📷 Экспорт PNG", self)
        act_png.setToolTip("Сохранить график в PNG")
        act_png.triggered.connect(self._export_png)
        toolbar.addAction(act_png)

        act_csv = QAction("📊 Экспорт CSV", self)
        act_csv.setToolTip("Сохранить историю итераций в CSV")
        act_csv.triggered.connect(self._export_csv)
        toolbar.addAction(act_csv)

    def _build_statusbar(self):
        self._status_bar = self.statusBar()
        self._status_label = QLabel("Готово")
        self._coords_label = QLabel("")
        self._status_bar.addWidget(self._status_label, stretch=1)
        self._status_bar.addPermanentWidget(self._coords_label)

    def _build_controller(self):
        parser = FunctionParser()
        evaluator = Evaluator()
        registry = FunctionRegistry()
        self._controller = Controller(
            parser,
            evaluator,
            registry,
            self._func_panel,
            self._algo_panel,
            self._plot_2d,
            self._plot_3d,
            self,
        )

    # ------------------------------------------------------------------
    # Public API for controller
    # ------------------------------------------------------------------

    def switch_plot_mode(self, mode: str):
        self._plot_stack.setCurrentIndex(0 if mode == "2d" else 1)

    def set_status(self, text: str):
        self._status_label.setText(text)

    def set_coords(self, x: float, y: float):
        self._coords_label.setText(f"x={x:.4f}  y={y:.4f}")

    def show_error(self, message: str):
        QMessageBox.warning(self, "Ошибка", message)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_png(self):
        exporter = PngExporter(parent=self)
        exporter.export(self._controller.get_current_plot())

    def _export_csv(self):
        exporter = CsvExporter(parent=self)
        exporter.export(self._controller.get_history())
