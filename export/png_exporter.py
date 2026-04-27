import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import pyqtgraph as pg
import pyqtgraph.exporters


class PngExporter:
    def __init__(self, parent=None):
        self._parent = parent

    def export(self, plot_widget, default_name: str = "plot.png"):
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Сохранить PNG", default_name, "PNG (*.png)"
        )
        if not path:
            return

        try:
            if hasattr(plot_widget, 'figure'):
                # Matplotlib canvas
                plot_widget.figure.savefig(path, dpi=150, bbox_inches='tight')
            elif hasattr(plot_widget, 'plotItem'):
                # pyqtgraph 2D
                exporter = pg.exporters.ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(path)
            else:
                img = plot_widget.grab().toImage()
                img.save(path, "PNG")
        except Exception as e:
            QMessageBox.critical(self._parent, "Ошибка", f"Не удалось сохранить PNG:\n{e}")
            return

        QMessageBox.information(self._parent, "Экспорт", f"Файл сохранён:\n{path}")
