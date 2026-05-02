import time

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class BenchmarkResult:
    """Stores raw data and computed statistics for one benchmark session."""

    def __init__(self, algo_name: str, func_expr: str, n_runs: int, epsilon: float):
        self.algo_name = algo_name
        self.func_expr = func_expr
        self.n_runs = n_runs
        self.epsilon = epsilon

        self.convergence_curves: list = []   # list[list[float]]  best_value per iter
        self.best_values: list = []          # list[float]  final best per run
        self.convergence_iters: list = []    # list[int|None]  iter of conv per run
        self.times: list = []                # list[float]  wall-clock seconds per run

        # Populated by finalize()
        self.mean_best: float = float('nan')
        self.std_best: float = float('nan')
        self.mean_convergence_iter = None    # float or None
        self.mean_time: float = float('nan')
        self.mean_curve: list = []
        self.min_curve: list = []
        self.max_curve: list = []

    def finalize(self):
        if not self.best_values:
            return
        arr = np.array(self.best_values, dtype=float)
        self.mean_best = float(np.mean(arr))
        self.std_best = float(np.std(arr))

        ci = [x for x in self.convergence_iters if x is not None]
        self.mean_convergence_iter = float(np.mean(ci)) if ci else None

        self.mean_time = float(np.mean(self.times)) if self.times else 0.0

        if self.convergence_curves:
            min_len = min(len(c) for c in self.convergence_curves)
            trimmed = np.array([c[:min_len] for c in self.convergence_curves], dtype=float)
            self.mean_curve = trimmed.mean(axis=0).tolist()
            self.min_curve = trimmed.min(axis=0).tolist()
            self.max_curve = trimmed.max(axis=0).tolist()


class BenchmarkWorker(QThread):
    """Runs an algorithm N times in background, emitting progress and result signals."""

    progress = pyqtSignal(int, int)   # (completed_runs, total_runs)
    finished = pyqtSignal(object)     # BenchmarkResult
    error = pyqtSignal(str)

    def __init__(self, algo_factory, n_runs: int, epsilon: float,
                 algo_name: str, func_expr: str, parent=None):
        super().__init__(parent)
        self._algo_factory = algo_factory
        self._n_runs = n_runs
        self._epsilon = epsilon
        self._algo_name = algo_name
        self._func_expr = func_expr
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            result = BenchmarkResult(
                self._algo_name, self._func_expr, self._n_runs, self._epsilon
            )

            for i in range(self._n_runs):
                if self._cancelled:
                    return

                algo = self._algo_factory()
                t0 = time.perf_counter()
                curve: list = []

                while algo.current_iter < algo.max_iter:
                    if self._cancelled:
                        return
                    state = algo.step()
                    bv = state.get('best_value', float('inf'))
                    curve.append(float(bv) if np.isfinite(bv) else float('inf'))

                elapsed = time.perf_counter() - t0

                if curve:
                    final_best = curve[-1]
                    result.convergence_curves.append(curve)
                    result.best_values.append(final_best)
                    result.times.append(elapsed)

                    # First iteration where value is within epsilon of the final best
                    conv_iter = None
                    for j, v in enumerate(curve):
                        if abs(v - final_best) <= self._epsilon:
                            conv_iter = j + 1
                            break
                    result.convergence_iters.append(conv_iter)

                self.progress.emit(i + 1, self._n_runs)

            result.finalize()
            self.finished.emit(result)

        except Exception as exc:
            self.error.emit(str(exc))
