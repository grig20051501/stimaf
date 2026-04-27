from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QGroupBox, QVBoxLayout
)


class AbcParamsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Параметры ABC")
        form = QFormLayout(group)

        self.n_bees = QSpinBox()
        self.n_bees.setRange(4, 1000)
        self.n_bees.setSingleStep(2)
        self.n_bees.setValue(40)
        self.n_bees.setToolTip("Общее число пчёл (половина — разведчики, половина — наблюдатели)")

        self.limit = QSpinBox()
        self.limit.setRange(1, 10000)
        self.limit.setValue(100)
        self.limit.setToolTip("Максимум попыток без улучшения до смены источника (scout phase)")

        self.max_iter = QSpinBox()
        self.max_iter.setRange(1, 10000)
        self.max_iter.setValue(100)

        form.addRow("Пчёл (всего):", self.n_bees)
        form.addRow("Лимит попыток:", self.limit)
        form.addRow("Итераций:", self.max_iter)

        layout.addWidget(group)

    def get_params(self) -> dict:
        return {
            'n_bees': self.n_bees.value(),
            'limit': self.limit.value(),
            'max_iter': self.max_iter.value(),
            'x_min': -5.0,
            'x_max':  5.0,
            'y_min': -5.0,
            'y_max':  5.0,
        }
