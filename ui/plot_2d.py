import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, QTimer


class Plot2DWidget(pg.PlotWidget):
    mouse_coords_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_appearance()

        # State for auto-redraw on zoom/pan
        self._evaluator = None
        self._entries = []
        self._x_bounds = (-5.0, 5.0)   # last set bounds (used as fallback)

        self._curves: dict = {}
        self._agent_scatter: pg.ScatterPlotItem = None
        self._best_marker: pg.ScatterPlotItem = None
        self._pheromone_img: pg.ImageItem = None

        # Debounce timer so we don't redraw on every tiny scroll tick
        self._redraw_timer = QTimer()
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(80)   # ms
        self._redraw_timer.timeout.connect(self._redraw_for_current_range)

        self.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.plotItem.vb.sigRangeChanged.connect(self._on_range_changed)

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------

    def _setup_appearance(self):
        self.setBackground('#1e1e2e')
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel('left', 'f(x)')
        self.setLabel('bottom', 'x')
        self.addLegend(offset=(10, 10))
        self.getPlotItem().setMenuEnabled(False)

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def update_functions(self, entries, evaluator, x_min: float, x_max: float):
        """Called by controller when function list or bounds change."""
        self._evaluator = evaluator
        self._entries = entries
        self._x_bounds = (x_min, x_max)
        self._draw_curves(x_min, x_max)

    def _draw_curves(self, x_min: float, x_max: float):
        """(Re)draw all function curves for the given x range."""
        if self._evaluator is None:
            return

        current_keys = {e.expr_str for e in self._entries}
        for key in list(self._curves.keys()):
            if key not in current_keys:
                self.removeItem(self._curves.pop(key))

        for entry in self._entries:
            x, y = self._evaluator.evaluate_2d(entry.func, x_min, x_max)
            r, g, b = entry.color
            pen = pg.mkPen(color=(r, g, b, 255), width=2)
            if entry.expr_str in self._curves:
                self._curves[entry.expr_str].setData(x, y)
            else:
                curve = self.plot(x, y, pen=pen, name=entry.expr_str)
                self._curves[entry.expr_str] = curve

    def _on_range_changed(self, _vb, _ranges):
        """Triggered on every zoom/pan — debounce before redrawing."""
        if self._entries and self._evaluator:
            self._redraw_timer.start()

    def _redraw_for_current_range(self):
        """Redraw curves for whatever x range is currently visible."""
        if not self._entries or self._evaluator is None:
            return
        vr = self.plotItem.vb.viewRange()
        x_min, x_max = float(vr[0][0]), float(vr[0][1])
        if np.isfinite(x_min) and np.isfinite(x_max) and x_max > x_min:
            self._x_bounds = (x_min, x_max)   # keep in sync with live viewport
            self._draw_curves(x_min, x_max)

    def get_x_bounds(self) -> tuple:
        """Current visible x range — used by the controller for algorithm bounds."""
        return self._x_bounds

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def update_agents(self, x_vals, y_vals, best_x=None, best_y=None):
        if x_vals is None or len(x_vals) == 0:
            self.clear_agents()
            return

        x_vals = np.asarray(x_vals, dtype=float)
        y_vals = np.asarray(y_vals, dtype=float)

        if self._agent_scatter is None:
            self._agent_scatter = pg.ScatterPlotItem(
                x=x_vals, y=y_vals,
                size=8, pen=pg.mkPen(None),
                brush=pg.mkBrush(255, 210, 0, 210),
            )
            self.addItem(self._agent_scatter)
        else:
            self._agent_scatter.setData(x=x_vals, y=y_vals)

        if best_x is not None and np.isfinite(best_y):
            if self._best_marker is None:
                self._best_marker = pg.ScatterPlotItem(
                    x=[best_x], y=[best_y],
                    size=18, symbol='star',
                    pen=pg.mkPen('r', width=2),
                    brush=pg.mkBrush(255, 60, 60, 230),
                )
                self.addItem(self._best_marker)
            else:
                self._best_marker.setData(x=[best_x], y=[best_y])

    def clear_agents(self):
        for item in (self._agent_scatter, self._best_marker):
            if item is not None:
                self.removeItem(item)
        self._agent_scatter = None
        self._best_marker = None

    # ------------------------------------------------------------------
    # Pheromone — 1-D
    # ------------------------------------------------------------------

    def update_pheromone(self, pheromone: np.ndarray, x_min: float, x_max: float):
        if pheromone is None or pheromone.ndim != 1:
            return

        pheromone = pheromone.astype(float)
        pmin, pmax = pheromone.min(), pheromone.max()
        norm = (pheromone - pmin) / (pmax - pmin + 1e-12)

        colormap = pg.colormap.get('viridis')
        rgba = colormap.map(norm, mode='byte')          # (N, 4)
        img_data = rgba[np.newaxis, :, :]               # (1, N, 4)

        if self._pheromone_img is None:
            self._pheromone_img = pg.ImageItem()
            self._pheromone_img.setZValue(-10)
            self.addItem(self._pheromone_img)

        vr = self.viewRange()
        y_bottom = vr[1][0]
        y_span = (vr[1][1] - vr[1][0]) * 0.04

        self._pheromone_img.setImage(img_data, autoLevels=False)
        self._pheromone_img.setRect(
            pg.QtCore.QRectF(x_min, y_bottom, x_max - x_min, y_span)
        )

    # ------------------------------------------------------------------
    # Pheromone — 2-D heatmap
    # ------------------------------------------------------------------

    def update_pheromone_2d(self, pheromone: np.ndarray,
                            x_min: float, x_max: float,
                            y_min: float, y_max: float):
        if pheromone is None or pheromone.ndim != 2:
            return

        pmin, pmax = pheromone.min(), pheromone.max()
        norm = (pheromone - pmin) / (pmax - pmin + 1e-12)

        colormap = pg.colormap.get('viridis')
        rgba = colormap.map(norm.ravel(), mode='byte').reshape(
            *norm.shape, 4
        ).astype(np.uint8)
        rgba[..., 3] = 110

        if self._pheromone_img is None:
            self._pheromone_img = pg.ImageItem()
            self._pheromone_img.setZValue(-10)
            self.addItem(self._pheromone_img)

        self._pheromone_img.setImage(rgba.transpose(1, 0, 2), autoLevels=False)
        self._pheromone_img.setRect(
            pg.QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
        )

    def clear_pheromone(self):
        if self._pheromone_img is not None:
            self.removeItem(self._pheromone_img)
            self._pheromone_img = None

    # ------------------------------------------------------------------
    # Mouse coords
    # ------------------------------------------------------------------

    def _on_mouse_moved(self, pos):
        if self.sceneBoundingRect().contains(pos):
            mp = self.plotItem.vb.mapSceneToView(pos)
            self.mouse_coords_changed.emit(mp.x(), mp.y())
