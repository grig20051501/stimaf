from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .params.abc_params import AbcParamsWidget
from .params.aco_params import AcoParamsWidget
from .params.pso_params import PsoParamsWidget

_ALGO_KEYS = ["pso", "aco", "abc"]


class AlgorithmPanel(QWidget):
    run_requested = pyqtSignal()
    step_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    algorithm_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Algorithm selector
        algo_group = QGroupBox("Алгоритм")
        algo_layout = QVBoxLayout(algo_group)
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(
            [
                "Рой частиц (PSO)",
                "Муравьиный (ACO)",
                "Рой пчёл (ABC)",
            ]
        )
        algo_layout.addWidget(self.algo_combo)
        layout.addWidget(algo_group)

        # Params stack
        self.params_stack = QStackedWidget()
        self.pso_params = PsoParamsWidget()
        self.aco_params = AcoParamsWidget()
        self.abc_params = AbcParamsWidget()
        self.params_stack.addWidget(self.pso_params)  # index 0
        self.params_stack.addWidget(self.aco_params)  # index 1
        self.params_stack.addWidget(self.abc_params)  # index 2
        layout.addWidget(self.params_stack)

        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)

        # Controls
        ctrl_group = QGroupBox("Управление")
        ctrl_layout = QVBoxLayout(ctrl_group)

        # Row 1: run (full width)
        self.run_btn = QPushButton("▶ Запустить")
        ctrl_layout.addWidget(self.run_btn)

        # Row 2: step navigation + reset
        btn_row = QHBoxLayout()
        self.step_back_btn = QPushButton("◀ Шаг назад")
        self.step_btn = QPushButton("Шаг вперёд ▶")
        self.reset_btn = QPushButton("↺ Сброс")
        self.step_back_btn.setEnabled(False)
        for b in (self.step_back_btn, self.step_btn, self.reset_btn):
            btn_row.addWidget(b)
        ctrl_layout.addLayout(btn_row)

        # Speed slider
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Скорость:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 20)
        self.speed_slider.setValue(5)
        self.speed_slider.setTickInterval(1)
        speed_row.addWidget(self.speed_slider)
        ctrl_layout.addLayout(speed_row)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        ctrl_layout.addWidget(self.progress_bar)

        # Result
        self.result_label = QLabel("Минимум: —")
        self.result_label.setObjectName("result_label")
        self.result_label.setWordWrap(True)
        ctrl_layout.addWidget(self.result_label)

        layout.addWidget(ctrl_group)
        layout.addStretch()

        self.run_btn.clicked.connect(self.run_requested)
        self.step_btn.clicked.connect(self.step_requested)
        self.reset_btn.clicked.connect(self.reset_requested)
        # step_back_btn is connected directly in the controller

    def _on_algo_changed(self, idx: int):
        self.params_stack.setCurrentIndex(idx)
        self.algorithm_changed.emit(_ALGO_KEYS[idx])

    def current_algorithm(self) -> str:
        return _ALGO_KEYS[self.algo_combo.currentIndex()]

    def get_pso_params(self) -> dict:
        return self.pso_params.get_params()

    def get_aco_params(self) -> dict:
        return self.aco_params.get_params()

    def get_abc_params(self) -> dict:
        return self.abc_params.get_params()

    def set_progress(self, current: int, total: int):
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def set_result(self, best_value: float, best_pos):
        coords = ", ".join(f"{v:.4f}" for v in best_pos)
        self.result_label.setText(f"Минимум: {best_value:.6f}\nКоорд: ({coords})")

    def set_running(self, running: bool):
        self.run_btn.setText("⏹ Стоп" if running else "▶ Запустить")
        self.step_btn.setEnabled(not running)
        if running:
            self.step_back_btn.setEnabled(False)
        self.algo_combo.setEnabled(not running)

    def update_y_visibility(self, is_3d: bool):
        self.pso_params.set_y_visible(is_3d)
