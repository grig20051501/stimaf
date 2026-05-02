import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.ticker import FuncFormatter, NullFormatter
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_BG = '#1e1e2e'
_AX_BG = '#181825'
_TEXT = '#cdd6f4'
_GRID = '#313244'
_SUBTEXT = '#6c7086'

_ALGO_COLORS = {
    'PSO': '#89b4fa',
    'ACO': '#a6e3a1',
    'ABC': '#fab387',
}
_ALGO_FULL = {
    'PSO': 'Рой частиц (PSO)',
    'ACO': 'Муравьиный (ACO)',
    'ABC': 'Рой пчёл (ABC)',
}

_MODE_ABSOLUTE = 0
_MODE_NORMALIZED = 1
_MODE_LOG = 2

_MODE_LABELS = [
    "Абсолютные значения",
    "Нормализованный зазор",
    "Логарифмическая шкала",
]


class BenchmarkTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: dict = {}   # algo_name -> BenchmarkResult
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        top_row = QHBoxLayout()

        self._status_lbl = QLabel("Нет данных — запустите бенчмарк на панели управления.")
        self._status_lbl.setObjectName("hint_label")
        top_row.addWidget(self._status_lbl, stretch=1)

        top_row.addWidget(QLabel("Режим:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(_MODE_LABELS)
        self._mode_combo.setCurrentIndex(_MODE_NORMALIZED)
        self._mode_combo.setMinimumWidth(200)
        self._mode_combo.currentIndexChanged.connect(lambda _: self._refresh_figure())
        top_row.addWidget(self._mode_combo)

        clear_btn = QPushButton("Очистить")
        clear_btn.setFixedWidth(90)
        clear_btn.clicked.connect(self.clear_results)
        top_row.addWidget(clear_btn)

        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._fig = Figure(facecolor=_BG, constrained_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)
        splitter.addWidget(self._canvas)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            'Алгоритм', 'Функция', 'Запусков',
            'f* (среднее)', 'σ(f*)',
            'Ит. сходимости', 'Время (мс)',
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        splitter.addWidget(self._table)

        splitter.setSizes([480, 160])
        layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_result(self, result) -> None:
        self._results[result.algo_name] = result
        self._refresh_figure()
        self._refresh_table()

    def clear_results(self) -> None:
        self._results.clear()
        self._fig.clear()
        self._canvas.draw()
        self._table.setRowCount(0)
        self._status_lbl.setText("Нет данных — запустите бенчмарк на панели управления.")

    # ------------------------------------------------------------------
    # Display-data helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_gap(curve, f_init, f_final):
        """Map curve to [0, 1] where 1 = initial, 0 = final best."""
        denom = f_init - f_final
        if abs(denom) < 1e-12:
            return [0.0] * len(curve)
        return [(v - f_final) / denom for v in curve]

    def _individual_display(self, res, mode: int):
        """Return (iters, mean, lo, hi, ylabel, use_log) for one algorithm."""
        mean = res.mean_curve
        lo   = res.min_curve
        hi   = res.max_curve
        iters = list(range(1, len(mean) + 1))

        if mode == _MODE_ABSOLUTE:
            return iters, mean, lo, hi, 'f* (лучшее)', False

        if mode == _MODE_NORMALIZED:
            f_init  = mean[0]  if mean else 1.0
            f_final = mean[-1] if mean else 0.0
            g_mean = self._normalize_gap(mean, f_init, f_final)
            g_lo   = self._normalize_gap(lo,   f_init, f_final)
            g_hi   = self._normalize_gap(hi,   f_init, f_final)
            return iters, g_mean, g_lo, g_hi, 'Нормализованный зазор', False

        # _MODE_LOG
        return iters, mean, lo, hi, 'f* (лог. масштаб)', True

    def _combined_display(self, results: list, mode: int):
        """
        Return per-algo (iters, curve) pairs + ylabel for the combined plot.

        Absolute / Log  → raw mean curves (absolute or log scale).
        Normalized      → cross-algo gap: each curve is measured against the
                          globally best final value found across all algorithms,
                          normalised by the global initial spread.
                          Penalises both slow convergence AND worse final quality.
        """
        if mode != _MODE_NORMALIZED:
            data = []
            for res in results:
                iters = list(range(1, len(res.mean_curve) + 1))
                data.append((res, iters, res.mean_curve))
            ylabel = ('f* (лучшее)'
                      if mode == _MODE_ABSOLUTE else 'f* (лог. масштаб)')
            use_log = (mode == _MODE_LOG)
            return data, ylabel, use_log

        # Cross-algo normalisation
        f_ref   = min(res.mean_curve[-1] for res in results if res.mean_curve)
        f_worst = max(res.mean_curve[0]  for res in results if res.mean_curve)
        denom   = f_worst - f_ref
        if abs(denom) < 1e-12:
            denom = 1.0

        data = []
        for res in results:
            iters = list(range(1, len(res.mean_curve) + 1))
            gap = [(v - f_ref) / denom for v in res.mean_curve]
            data.append((res, iters, gap))

        return data, 'Отн. зазор до глоб. минимума', False

    # ------------------------------------------------------------------
    # Figure
    # ------------------------------------------------------------------

    def _refresh_figure(self):
        self._fig.clear()
        results = list(self._results.values())
        n = len(results)
        if n == 0:
            self._canvas.draw()
            return

        mode = self._mode_combo.currentIndex()

        if n == 1:
            ax_ind  = [self._fig.add_subplot(1, 1, 1)]
            ax_comb = None
        else:
            gs      = self._fig.add_gridspec(2, n, height_ratios=[1.0, 0.75])
            ax_ind  = [self._fig.add_subplot(gs[0, i]) for i in range(n)]
            ax_comb = self._fig.add_subplot(gs[1, :])

        for ax, res in zip(ax_ind, results):
            self._draw_individual(ax, res, mode)

        if ax_comb is not None:
            self._draw_combined(ax_comb, results, mode)

        self._canvas.draw()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _style_ax(self, ax, title: str, xlabel: str = 'Итерация', ylabel: str = ''):
        ax.set_facecolor(_AX_BG)
        ax.set_title(title, color=_TEXT, fontsize=8.5, pad=4)
        ax.set_xlabel(xlabel, color=_SUBTEXT, fontsize=7.5)
        ax.set_ylabel(ylabel, color=_SUBTEXT, fontsize=7.5)
        ax.tick_params(colors=_TEXT, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(_GRID)
        ax.grid(True, color=_GRID, linewidth=0.5, linestyle='--')

    def _add_legend(self, ax):
        legend = ax.legend(fontsize=7, facecolor=_AX_BG, edgecolor=_GRID)
        for text in legend.get_texts():
            text.set_color(_TEXT)

    def _apply_log(self, ax, curves: list):
        """Try log scale; fall back to symlog if values ≤ 0. Use plain decimal ticks."""
        all_vals = [v for c in curves for v in c if np.isfinite(v)]
        if not all_vals:
            return
        if min(all_vals) > 0:
            ax.set_yscale('log')
        else:
            linthresh = max((abs(v) for v in all_vals if v != 0), default=1e-6) * 0.001
            ax.set_yscale('symlog', linthresh=max(linthresh, 1e-6))

        # Replace default "3 × 10⁻¹" notation with plain decimals: 0.3, 0.1, 0.06 …
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.4g}'))
        ax.yaxis.set_minor_formatter(NullFormatter())

    def _draw_individual(self, ax, res, mode: int):
        color = _ALGO_COLORS.get(res.algo_name, '#cdd6f4')
        iters, mean, lo, hi, ylabel, use_log = self._individual_display(res, mode)

        if not use_log:
            ax.fill_between(iters, lo, hi, color=color, alpha=0.18)
        ax.plot(iters, mean, color=color, linewidth=2,
                label=f'Среднее ({res.n_runs} зап.)')

        if use_log:
            self._apply_log(ax, [mean])

        full_name = _ALGO_FULL.get(res.algo_name, res.algo_name)
        self._style_ax(ax, f'{full_name}\n{res.func_expr}', ylabel=ylabel)
        self._add_legend(ax)

        if mode == _MODE_NORMALIZED:
            ax.set_ylim(-0.05, 1.1)
            ax.axhline(0, color=color, linewidth=0.6, linestyle=':')

    def _draw_combined(self, ax, results: list, mode: int):
        data, ylabel, use_log = self._combined_display(results, mode)

        for res, iters, curve in data:
            color = _ALGO_COLORS.get(res.algo_name, '#cdd6f4')
            label = _ALGO_FULL.get(res.algo_name, res.algo_name)
            ax.plot(iters, curve, color=color, linewidth=2, label=label)

        if use_log:
            self._apply_log(ax, [d[2] for d in data])

        if mode == _MODE_NORMALIZED:
            title = 'Сравнение: относительный зазор до глобального минимума'
            subtitle = ('0 = лучший найденный результат среди всех алгоритмов')
            ax.set_title(f'{title}\n{subtitle}', color=_TEXT, fontsize=8, pad=4)
            ax.axhline(0, color='#f38ba8', linewidth=0.8, linestyle='--',
                       label='Глоб. минимум')
            best_val = min(res.mean_curve[-1]
                           for res in results if res.mean_curve)
            ax.annotate(f'f*={best_val:.6g}', xy=(1, 0),
                        xycoords=('axes fraction', 'data'),
                        xytext=(-6, 6), textcoords='offset points',
                        ha='right', va='bottom',
                        color='#f38ba8', fontsize=7)
        else:
            ax.set_title('Сравнение алгоритмов (средние кривые)',
                         color=_TEXT, fontsize=8.5, pad=4)

        ax.set_xlabel('Итерация', color=_SUBTEXT, fontsize=7.5)
        ax.set_ylabel(ylabel, color=_SUBTEXT, fontsize=7.5)
        ax.set_facecolor(_AX_BG)
        ax.tick_params(colors=_TEXT, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(_GRID)
        ax.grid(True, color=_GRID, linewidth=0.5, linestyle='--')

        legend = ax.legend(fontsize=8, facecolor=_AX_BG, edgecolor=_GRID)
        for text in legend.get_texts():
            text.set_color(_TEXT)

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------

    def _refresh_table(self):
        self._table.setRowCount(len(self._results))
        for row, res in enumerate(self._results.values()):
            ci_str = (f'{res.mean_convergence_iter:.1f}'
                      if res.mean_convergence_iter is not None else '—')
            cells = [
                res.algo_name,
                res.func_expr,
                str(res.n_runs),
                f'{res.mean_best:.6g}',
                f'{res.std_best:.6g}',
                ci_str,
                f'{res.mean_time * 1000:.1f}',
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)

        count = len(self._results)
        label = f'Результаты: {count} алгоритм{"ов" if count != 1 else ""}'
        self._status_lbl.setText(label)
