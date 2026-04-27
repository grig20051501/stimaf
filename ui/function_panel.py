from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QButtonGroup, QRadioButton,
    QGroupBox, QLabel, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor


class FunctionPanel(QWidget):
    function_added = pyqtSignal(str)        # expr_str
    function_removed = pyqtSignal(str)      # expr_str
    mode_changed = pyqtSignal(str)          # '2d' or '3d'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- Input area ---
        input_group = QGroupBox("Функция")
        input_layout = QVBoxLayout(input_group)

        hint = QLabel("Переменные: x (2D), x и y (3D)")
        hint.setObjectName("hint_label")
        input_layout.addWidget(hint)

        row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("например: sin(x)*cos(x)")
        self.input_edit.returnPressed.connect(self._on_add)
        row.addWidget(self.input_edit)

        self.add_btn = QPushButton("Добавить")
        self.add_btn.setFixedWidth(90)
        self.add_btn.clicked.connect(self._on_add)
        row.addWidget(self.add_btn)
        input_layout.addLayout(row)

        layout.addWidget(input_group)

        # --- Functions list ---
        list_group = QGroupBox("Активные функции")
        list_layout = QVBoxLayout(list_group)
        self.func_list = QListWidget()
        self.func_list.setSpacing(2)
        list_layout.addWidget(self.func_list)
        layout.addWidget(list_group)

        # --- Mode switcher ---
        mode_group = QGroupBox("Режим отображения")
        mode_layout = QHBoxLayout(mode_group)
        self._mode_group = QButtonGroup(self)
        self.radio_2d = QRadioButton("2D")
        self.radio_3d = QRadioButton("3D")
        self.radio_2d.setChecked(True)
        self._mode_group.addButton(self.radio_2d)
        self._mode_group.addButton(self.radio_3d)
        mode_layout.addWidget(self.radio_2d)
        mode_layout.addWidget(self.radio_3d)
        layout.addWidget(mode_group)

        self.radio_2d.toggled.connect(lambda checked: self.mode_changed.emit('2d') if checked else None)
        self.radio_3d.toggled.connect(lambda checked: self.mode_changed.emit('3d') if checked else None)

    def _on_add(self):
        text = self.input_edit.text().strip()
        if text:
            self.function_added.emit(text)

    def add_function_item(self, expr_str: str, color: tuple):
        """Called by controller after successful parse."""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, expr_str)

        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(4, 2, 4, 2)

        color_dot = QLabel("●")
        color_dot.setStyleSheet(f"color: rgb({color[0]},{color[1]},{color[2]}); font-size: 18px;")
        row.addWidget(color_dot)

        label = QLabel(expr_str)
        label.setToolTip(expr_str)
        row.addWidget(label, stretch=1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setObjectName("remove_btn")
        remove_btn.clicked.connect(lambda _, e=expr_str: self._remove(e))
        row.addWidget(remove_btn)

        self.func_list.addItem(item)
        item.setSizeHint(widget.sizeHint())
        self.func_list.setItemWidget(item, widget)

        self.input_edit.clear()

    def _remove(self, expr_str: str):
        for i in range(self.func_list.count()):
            item = self.func_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == expr_str:
                self.func_list.takeItem(i)
                break
        self.function_removed.emit(expr_str)

    def remove_function_item(self, expr_str: str):
        for i in range(self.func_list.count()):
            item = self.func_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == expr_str:
                self.func_list.takeItem(i)
                break

    def show_error(self, message: str):
        QMessageBox.warning(self, "Ошибка ввода", message)

    @property
    def mode(self) -> str:
        return '3d' if self.radio_3d.isChecked() else '2d'
