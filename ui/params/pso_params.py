from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QGroupBox, QVBoxLayout
)



class PsoParamsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Параметры PSO")
        form = QFormLayout(group)

        self.n_particles = QSpinBox()
        self.n_particles.setRange(5, 500)
        self.n_particles.setValue(30)

        self.inertia = QDoubleSpinBox()
        self.inertia.setRange(0.01, 2.0)
        self.inertia.setSingleStep(0.05)
        self.inertia.setValue(0.7)

        self.cognitive = QDoubleSpinBox()
        self.cognitive.setRange(0.0, 4.0)
        self.cognitive.setSingleStep(0.1)
        self.cognitive.setValue(1.5)

        self.social = QDoubleSpinBox()
        self.social.setRange(0.0, 4.0)
        self.social.setSingleStep(0.1)
        self.social.setValue(1.5)

        self.max_iter = QSpinBox()
        self.max_iter.setRange(1, 10000)
        self.max_iter.setValue(100)

        form.addRow("Частиц:", self.n_particles)
        form.addRow("Инерция:", self.inertia)
        form.addRow("Когнитивный:", self.cognitive)
        form.addRow("Социальный:", self.social)
        form.addRow("Итераций:", self.max_iter)

        layout.addWidget(group)

    def get_params(self) -> dict:
        return {
            'n_particles': self.n_particles.value(),
            'inertia': self.inertia.value(),
            'cognitive': self.cognitive.value(),
            'social': self.social.value(),
            'max_iter': self.max_iter.value(),
            'x_min': -5.0,
            'x_max':  5.0,
            'y_min': -5.0,
            'y_max':  5.0,
        }

    def set_y_visible(self, visible: bool):
        pass
