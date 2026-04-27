from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QGroupBox, QVBoxLayout
)


class AcoParamsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Параметры ACO")
        form = QFormLayout(group)

        self.n_ants = QSpinBox()
        self.n_ants.setRange(5, 500)
        self.n_ants.setValue(30)

        self.evaporation = QDoubleSpinBox()
        self.evaporation.setRange(0.01, 0.99)
        self.evaporation.setSingleStep(0.05)
        self.evaporation.setValue(0.5)

        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(0.0, 10.0)
        self.alpha.setSingleStep(0.1)
        self.alpha.setValue(1.0)

        self.beta = QDoubleSpinBox()
        self.beta.setRange(0.0, 10.0)
        self.beta.setSingleStep(0.1)
        self.beta.setValue(2.0)

        self.grid_resolution = QSpinBox()
        self.grid_resolution.setRange(5, 200)
        self.grid_resolution.setValue(50)

        self.max_iter = QSpinBox()
        self.max_iter.setRange(1, 10000)
        self.max_iter.setValue(100)

        form.addRow("Муравьёв:", self.n_ants)
        form.addRow("Испарение:", self.evaporation)
        form.addRow("Alpha (ферм.):", self.alpha)
        form.addRow("Beta (эврист.):", self.beta)
        form.addRow("Разрешение сетки:", self.grid_resolution)
        form.addRow("Итераций:", self.max_iter)

        layout.addWidget(group)

    def get_params(self) -> dict:
        return {
            'n_ants': self.n_ants.value(),
            'evaporation': self.evaporation.value(),
            'alpha': self.alpha.value(),
            'beta': self.beta.value(),
            'grid_resolution': self.grid_resolution.value(),
            'max_iter': self.max_iter.value(),
            'x_min': -5.0,
            'x_max':  5.0,
            'y_min': -5.0,
            'y_max':  5.0,
        }
