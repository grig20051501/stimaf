import csv
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox


class CsvExporter:
    def __init__(self, parent=None):
        self._parent = parent

    def export(self, history: list, default_name: str = "history.csv"):
        if not history:
            QMessageBox.information(self._parent, "Экспорт CSV", "История итераций пуста.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Сохранить CSV", default_name, "CSV (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                first = history[0]
                n_agents = len(first.get('positions', []))
                dim = first['positions'].shape[1] if n_agents else 0

                header = ['iteration', 'best_value']
                for d in range(dim):
                    header.append(f'best_pos_{d}')
                for i in range(n_agents):
                    for d in range(dim):
                        header.append(f'agent_{i}_pos_{d}')
                writer.writerow(header)

                for state in history:
                    it = state['iteration']
                    bv = state['best_value']
                    bp = state.get('best_position', [])
                    positions = state.get('positions', [])
                    row = [it, bv] + list(bp)
                    for pos in positions:
                        row.extend(list(pos))
                    writer.writerow(row)

        except Exception as e:
            QMessageBox.critical(self._parent, "Ошибка", f"Не удалось сохранить CSV:\n{e}")
            return

        QMessageBox.information(self._parent, "Экспорт", f"Файл сохранён:\n{path}")
