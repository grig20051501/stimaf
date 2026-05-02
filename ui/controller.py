import copy
import numpy as np
from PyQt6.QtCore import QTimer

from core import FunctionParser, Evaluator, FunctionRegistry
from algorithms import PSO, ACO, ABC
from benchmark.runner import BenchmarkWorker


class Controller:
    def __init__(self, parser: FunctionParser, evaluator: Evaluator,
                 registry: FunctionRegistry, func_panel, algo_panel,
                 plot_2d, plot_3d, main_window):
        self._parser = parser
        self._evaluator = evaluator
        self._registry = registry
        self._func_panel = func_panel
        self._algo_panel = algo_panel
        self._plot_2d = plot_2d
        self._plot_3d = plot_3d
        self._main_window = main_window

        self._algorithm = None
        self._current_mode: str = '2d'
        self._running: bool = False
        self._state_stack: list = []   # deepcopied algorithm states for step-back
        self._MAX_STACK = 60

        self._bench_worker: BenchmarkWorker = None

        self._timer = QTimer()
        self._timer.timeout.connect(self._on_timer_tick)

        self._connect_signals()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self._func_panel.function_added.connect(self._on_function_added)
        self._func_panel.function_removed.connect(self._on_function_removed)
        self._func_panel.mode_changed.connect(self._on_mode_changed)

        self._algo_panel.run_btn.clicked.connect(self._on_run_clicked)
        self._algo_panel.step_btn.clicked.connect(self._on_step_clicked)
        self._algo_panel.step_back_btn.clicked.connect(self._on_step_back_clicked)
        self._algo_panel.reset_btn.clicked.connect(self._on_reset_clicked)
        self._algo_panel.speed_slider.valueChanged.connect(self._on_speed_changed)
        self._algo_panel.bench_run_btn.clicked.connect(self._on_bench_clicked)

        self._plot_2d.mouse_coords_changed.connect(self._on_mouse_coords)

    # ------------------------------------------------------------------
    # Function management
    # ------------------------------------------------------------------

    def _on_function_added(self, expr_str: str):
        try:
            func, variables, _ = self._parser.parse(expr_str)
        except ValueError as e:
            self._func_panel.show_error(str(e))
            return

        entry = self._registry.add(expr_str, func, variables)
        self._func_panel.add_function_item(expr_str, entry.color)
        self._refresh_plot()

    def _on_function_removed(self, expr_str: str):
        self._registry.remove(expr_str)
        self._refresh_plot()

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _on_mode_changed(self, mode: str):
        self._current_mode = mode
        self._main_window.switch_plot_mode(mode)
        self._refresh_plot()
        is_3d = (mode == '3d')
        self._algo_panel.update_y_visibility(is_3d)

    # ------------------------------------------------------------------
    # Refresh plots
    # ------------------------------------------------------------------

    def _refresh_plot(self):
        entries = self._registry.entries
        p = self._get_params()

        if self._current_mode == '2d':
            entries_2d = [e for e in entries if len(e.variables) == 1]
            self._plot_2d.update_functions(entries_2d, self._evaluator, p['x_min'], p['x_max'])
        else:
            entries_3d = [e for e in entries if len(e.variables) == 2]
            self._plot_3d.update_functions(
                entries_3d, self._evaluator,
                p['x_min'], p['x_max'], p['y_min'], p['y_max']
            )

    # ------------------------------------------------------------------
    # Algorithm management
    # ------------------------------------------------------------------

    def _get_params(self) -> dict:
        algo = self._algo_panel.current_algorithm()
        if algo == 'pso':
            p = self._algo_panel.get_pso_params()
        elif algo == 'aco':
            p = self._algo_panel.get_aco_params()
        else:
            p = self._algo_panel.get_abc_params()

        # Bounds come from the 2D plot's current visible x range.
        # _x_bounds is updated every time the user zooms or pans in 2D mode,
        # so the algorithm always searches exactly the visible window.
        # For 3D the y range mirrors x (symmetric square domain).
        x_min, x_max = self._plot_2d.get_x_bounds()
        p['x_min'] = x_min
        p['x_max'] = x_max
        p['y_min'] = x_min
        p['y_max'] = x_max
        return p

    def _get_target_func(self):
        """Return the function to optimize (first matching entry)."""
        entries = self._registry.entries
        target_dim = 2 if self._current_mode == '3d' else 1
        for e in entries:
            if len(e.variables) == target_dim:
                return e.func, e.variables
        if entries:
            return entries[0].func, entries[0].variables
        return None, None

    def _build_algorithm(self):
        func, variables = self._get_target_func()
        if func is None:
            self._main_window.show_error("Сначала добавьте функцию.")
            return None

        p = self._get_params()
        dim = len(variables)
        bounds = [(p['x_min'], p['x_max'])]
        if dim == 2:
            bounds.append((p['y_min'], p['y_max']))

        algo_name = self._algo_panel.current_algorithm()
        if algo_name == 'pso':
            return PSO(
                func, bounds,
                n_particles=p['n_particles'],
                inertia=p['inertia'],
                cognitive=p['cognitive'],
                social=p['social'],
                max_iter=p['max_iter'],
            )
        if algo_name == 'aco':
            return ACO(
                func, bounds,
                n_ants=p['n_ants'],
                evaporation=p['evaporation'],
                alpha=p['alpha'],
                beta=p['beta'],
                grid_resolution=p['grid_resolution'],
                max_iter=p['max_iter'],
            )
        # abc
        return ABC(
            func, bounds,
            n_bees=p['n_bees'],
            limit=p['limit'],
            max_iter=p['max_iter'],
        )

    # ------------------------------------------------------------------
    # Run / Step / Reset
    # ------------------------------------------------------------------

    def _on_run_clicked(self):
        if self._running:
            self._stop()
            return
        self._algorithm = self._build_algorithm()
        if self._algorithm is None:
            return
        self._state_stack.clear()
        self._running = True
        self._algo_panel.set_running(True)
        delay = max(10, 210 // self._algo_panel.speed_slider.value())
        self._timer.start(delay)

    def _stop(self):
        self._timer.stop()
        self._running = False
        self._algo_panel.set_running(False)
        self._refresh_back_btn()

    def _on_timer_tick(self):
        if self._algorithm is None:
            self._stop()
            return
        self._push_state()
        state = self._algorithm.step()
        self._apply_state(state)
        if self._algorithm.current_iter >= self._algorithm.max_iter:
            self._stop()

    def _on_step_clicked(self):
        if self._algorithm is None:
            self._algorithm = self._build_algorithm()
        if self._algorithm and self._algorithm.current_iter < self._algorithm.max_iter:
            self._push_state()
            state = self._algorithm.step()
            self._apply_state(state)
            self._refresh_back_btn()

    def _on_step_back_clicked(self):
        if not self._state_stack:
            return
        self._algorithm = self._state_stack.pop()
        if self._algorithm._history:
            state = self._algorithm._history[-1]
            self._apply_state(state)
        else:
            # Restored to before first step — clear display
            self._plot_2d.clear_agents()
            self._plot_3d.clear_agents()
            self._algo_panel.set_progress(0, self._algorithm.max_iter)
            self._algo_panel.result_label.setText("Минимум: —")
            self._main_window.set_status("Готово")
        self._refresh_back_btn()

    def _push_state(self):
        self._state_stack.append(copy.deepcopy(self._algorithm))
        if len(self._state_stack) > self._MAX_STACK:
            self._state_stack.pop(0)

    def _refresh_back_btn(self):
        self._algo_panel.step_back_btn.setEnabled(
            bool(self._state_stack) and not self._running
        )

    def _on_speed_changed(self, val: int):
        if self._running:
            delay = max(10, 210 // val)
            self._timer.setInterval(delay)

    def _on_reset_clicked(self):
        self._stop()
        self._state_stack.clear()
        if self._algorithm:
            self._algorithm.reset()
        self._plot_2d.clear_agents()
        self._plot_2d.clear_pheromone()
        self._plot_3d.clear_agents()
        self._plot_3d.clear_pheromone()
        self._algo_panel.set_progress(0, 1)
        self._algo_panel.result_label.setText("Минимум: —")
        self._main_window.set_status("Готово")
        self._refresh_back_btn()

    # ------------------------------------------------------------------
    # State → visualization
    # ------------------------------------------------------------------

    def _apply_state(self, state: dict):
        p = self._get_params()
        func, variables = self._get_target_func()
        algo = self._algorithm
        self._algo_panel.set_progress(state['iteration'], algo.max_iter)

        bp = state.get('best_position', np.array([]))
        bv = state.get('best_value', float('inf'))
        if len(bp) > 0 and np.isfinite(bv):
            self._algo_panel.set_result(bv, bp)

        positions = state.get('positions', np.zeros((0, 1)))

        if self._current_mode == '2d':
            self._apply_state_2d(state, positions, bp, bv, p, func)
        else:
            self._apply_state_3d(state, positions, bp, bv, p, func)

        self._update_status(state)

    def _apply_state_2d(self, state, positions, bp, bv, p, func):
        if positions.shape[0] == 0:
            return

        x_vals = positions[:, 0]
        if func is not None:
            y_vals = np.array([self._safe_eval_1d(func, x) for x in x_vals])
        else:
            y_vals = np.zeros_like(x_vals)

        best_x = float(bp[0]) if len(bp) > 0 else None
        best_y = self._safe_eval_1d(func, best_x) if (best_x is not None and func) else None

        self._plot_2d.update_agents(x_vals, y_vals, best_x, best_y)

    def _apply_state_3d(self, state, positions, bp, bv, p, func):
        if positions.shape[0] == 0 or positions.shape[1] < 2:
            return

        algo_key = self._algo_panel.current_algorithm()
        _LABELS = {'pso': 'Частицы', 'aco': 'Муравьи', 'abc': 'Пчёлы'}
        self._plot_3d.set_agent_label(_LABELS.get(algo_key, 'Агенты'))

        z_vals = np.array([self._safe_eval_2d(func, pos) for pos in positions])
        best_xyz = None
        if len(bp) >= 2:
            bz = self._safe_eval_2d(func, bp)
            best_xyz = np.array([bp[0], bp[1], bz])

        self._plot_3d.update_agents(positions[:, :2], z_vals, best_xyz)

        pheromone = state.get('pheromone')
        if pheromone is not None and pheromone.ndim == 2:
            self._plot_3d.update_pheromone(
                pheromone, p['x_min'], p['x_max'], p['y_min'], p['y_max']
            )

    def _safe_eval_1d(self, func, x) -> float:
        try:
            return float(func(x))
        except Exception:
            return float('nan')

    def _safe_eval_2d(self, func, pos) -> float:
        try:
            return float(func(pos[0], pos[1]))
        except Exception:
            return float('nan')

    def _update_status(self, state: dict):
        it = state.get('iteration', 0)
        total = self._algorithm.max_iter if self._algorithm else 0
        bv = state.get('best_value', float('inf'))
        _NAMES = {'pso': 'PSO', 'aco': 'ACO', 'abc': 'ABC'}
        algo_key = self._algo_panel.current_algorithm()
        algo_name = _NAMES.get(algo_key, algo_key.upper())
        self._main_window.set_status(
            f"Алгоритм: {algo_name}  |  Итерация: {it}/{total}  |  Минимум: {bv:.6f}"
        )
        if self._current_mode == '3d':
            entries = self._registry.entries
            func_label = entries[0].expr_str if entries else ''
            _FULL = {'pso': 'Алгоритм роя частиц', 'aco': 'Муравьиный алгоритм',
                     'abc': 'Алгоритм роя пчёл'}
            title = f"{_FULL.get(algo_key, algo_name)}: {func_label}"
            self._plot_3d.set_title(title)

    # ------------------------------------------------------------------
    # Mouse coords
    # ------------------------------------------------------------------

    def _on_mouse_coords(self, x: float, y: float):
        self._main_window.set_coords(x, y)

    # ------------------------------------------------------------------
    # Benchmark
    # ------------------------------------------------------------------

    def _on_bench_clicked(self):
        if self._bench_worker and self._bench_worker.isRunning():
            self._bench_worker.cancel()
            self._algo_panel.set_bench_running(False)
            self._main_window.set_status("Бенчмарк отменён")
            return

        func, variables = self._get_target_func()
        if func is None:
            self._main_window.show_error("Сначала добавьте функцию.")
            return

        entries = self._registry.entries
        func_expr = entries[0].expr_str if entries else '?'
        algo_name = self._algo_panel.current_algorithm().upper()
        n_runs = self._algo_panel.bench_n_runs.value()
        epsilon = self._algo_panel.bench_epsilon.value()

        factory = self._make_algo_factory()
        if factory is None:
            return

        self._bench_worker = BenchmarkWorker(
            factory, n_runs, epsilon, algo_name, func_expr
        )
        self._bench_worker.progress.connect(self._on_bench_progress)
        self._bench_worker.finished.connect(self._on_bench_finished)
        self._bench_worker.error.connect(self._on_bench_error)

        self._algo_panel.set_bench_running(True)
        self._main_window.set_status(
            f"Бенчмарк {algo_name}: запуск 0/{n_runs}…"
        )
        self._bench_worker.start()

    def _make_algo_factory(self):
        """Return a no-arg callable that builds a fresh algorithm instance."""
        func, variables = self._get_target_func()
        if func is None:
            return None

        p = self._get_params()
        dim = len(variables)
        bounds = [(p['x_min'], p['x_max'])]
        if dim == 2:
            bounds.append((p['y_min'], p['y_max']))

        algo_key = self._algo_panel.current_algorithm()

        if algo_key == 'pso':
            def factory():
                return PSO(func, bounds,
                           n_particles=p['n_particles'], inertia=p['inertia'],
                           cognitive=p['cognitive'], social=p['social'],
                           max_iter=p['max_iter'])
        elif algo_key == 'aco':
            def factory():
                return ACO(func, bounds,
                           n_ants=p['n_ants'], evaporation=p['evaporation'],
                           alpha=p['alpha'], beta=p['beta'],
                           grid_resolution=p['grid_resolution'],
                           max_iter=p['max_iter'])
        else:
            def factory():
                return ABC(func, bounds,
                           n_bees=p['n_bees'], limit=p['limit'],
                           max_iter=p['max_iter'])

        return factory

    def _on_bench_progress(self, done: int, total: int):
        self._algo_panel.set_bench_progress(done, total)
        self._main_window.set_status(
            f"Бенчмарк: запуск {done}/{total}…"
        )

    def _on_bench_finished(self, result):
        self._algo_panel.set_bench_running(False)
        self._main_window.benchmark_tab.add_result(result)
        self._main_window.show_benchmark_tab()
        ci_str = (f'{result.mean_convergence_iter:.1f}'
                  if result.mean_convergence_iter is not None else '—')
        self._main_window.set_status(
            f"Бенчмарк {result.algo_name} завершён  |  "
            f"f*={result.mean_best:.6g}  σ={result.std_best:.6g}  "
            f"ит.сх.={ci_str}  "
            f"время={result.mean_time * 1000:.1f} мс/запуск"
        )

    def _on_bench_error(self, msg: str):
        self._algo_panel.set_bench_running(False)
        self._main_window.show_error(f"Ошибка бенчмарка:\n{msg}")

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def get_current_plot(self):
        return self._plot_2d if self._current_mode == '2d' else self._plot_3d

    def get_history(self) -> list:
        if self._algorithm:
            return self._algorithm.get_history()
        return []
