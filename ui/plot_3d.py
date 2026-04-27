import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers '3d' projection

_CMAPS = ['viridis', 'plasma', 'inferno', 'magma', 'cividis']

_AGENT_LABELS = {
    'pso': 'Частицы',
    'aco': 'Муравьи',
    'abc': 'Пчёлы',
}


class Plot3DWidget(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        fig = Figure(dpi=100)
        super().__init__(fig)
        self._fig = fig

        self._evaluator = None
        self._entries = []
        self._x_bounds = (-5.0, 5.0)
        self._y_bounds = (-5.0, 5.0)
        self._cmap_idx: dict = {}        # expr_str → cmap index
        self._title_text = ''
        self._agent_label = 'Агенты'
        self._z_data_min: float = None  # actual function z-min, used as pheromone floor
        self._z_data_max: float = None

        self._ax: Axes3D = None
        self._surface_arts: dict = {}   # expr_str → surface
        self._agent_art = None
        self._best_art = None
        self._pheromone_art = None

        self._init_axes()

    # ------------------------------------------------------------------
    # Axes management
    # ------------------------------------------------------------------

    def _init_axes(self, restore_view=None):
        self._fig.clear()
        self._fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.93)
        ax = self._fig.add_subplot(111, projection='3d')
        self._ax = ax

        ax.set_xlabel('X', labelpad=6)
        ax.set_ylabel('Y', labelpad=6)
        ax.set_zlabel('f(x, y)', labelpad=6)
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.35)

        if self._title_text:
            ax.set_title(self._title_text, fontsize=10, pad=8)

        elev, azim = restore_view if restore_view else (25, -50)
        ax.view_init(elev=elev, azim=azim)

        self._surface_arts.clear()
        self._agent_art = None
        self._best_art = None
        self._pheromone_art = None

    def _current_view(self):
        if self._ax is not None:
            return self._ax.elev, self._ax.azim
        return 25, -50

    # ------------------------------------------------------------------
    # Functions (surfaces)
    # ------------------------------------------------------------------

    def update_functions(self, entries, evaluator, x_min, x_max, y_min, y_max):
        self._evaluator = evaluator
        self._entries = entries
        self._x_bounds = (x_min, x_max)
        self._y_bounds = (y_min, y_max)
        self._redraw_surfaces()

    def _redraw_surfaces(self):
        view = self._current_view()
        self._init_axes(restore_view=view)
        self._z_data_min = None
        self._z_data_max = None

        for entry in self._entries:
            if entry.expr_str not in self._cmap_idx:
                self._cmap_idx[entry.expr_str] = len(self._cmap_idx) % len(_CMAPS)
            cmap = _CMAPS[self._cmap_idx[entry.expr_str]]

            x_min, x_max = self._x_bounds
            y_min, y_max = self._y_bounds
            X, Y, Z = self._evaluator.evaluate_3d(
                entry.func, x_min, x_max, y_min, y_max
            )
            surf = self._ax.plot_surface(
                X, Y, Z,
                cmap=cmap,
                alpha=0.85,
                linewidth=0,
                antialiased=True,
                zorder=1,
            )
            self._surface_arts[entry.expr_str] = surf

            # Track actual z range so pheromone floor is correct
            finite_z = Z[np.isfinite(Z)]
            if len(finite_z):
                zmin, zmax = float(finite_z.min()), float(finite_z.max())
                self._z_data_min = zmin if self._z_data_min is None else min(self._z_data_min, zmin)
                self._z_data_max = zmax if self._z_data_max is None else max(self._z_data_max, zmax)

        self.draw_idle()

    # ------------------------------------------------------------------
    # Title / labels
    # ------------------------------------------------------------------

    def set_title(self, text: str):
        self._title_text = text
        if self._ax is not None:
            self._ax.set_title(text, fontsize=10, pad=8)
            self.draw_idle()

    def set_agent_label(self, label: str):
        self._agent_label = label

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def update_agents(self, positions_xy, z_values, best_xyz=None):
        if positions_xy is None or len(positions_xy) == 0:
            self.clear_agents()
            return

        positions_xy = np.asarray(positions_xy, dtype=float)
        z_values = np.asarray(z_values, dtype=float)
        zs = np.where(np.isfinite(z_values), z_values, 0.0)
        xs, ys = positions_xy[:, 0], positions_xy[:, 1]

        # Remove stale artists, re-add (avoids _offsets3d depth-shading glitches)
        if self._agent_art is not None:
            self._agent_art.remove()
            self._agent_art = None
        self._agent_art = self._ax.scatter(
            xs, ys, zs,
            s=30, c='#222222', marker='o',
            depthshade=True, zorder=5,
            label=self._agent_label,
        )

        if self._best_art is not None:
            self._best_art.remove()
            self._best_art = None
        if best_xyz is not None and len(best_xyz) >= 3 and np.isfinite(best_xyz[2]):
            bx, by, bz = float(best_xyz[0]), float(best_xyz[1]), float(best_xyz[2])
            self._best_art = self._ax.scatter(
                [bx], [by], [bz],
                s=140, c='red', marker='x',
                linewidths=2.5, zorder=6,
                label='Найденный минимум',
            )

        handles = [a for a in (self._agent_art, self._best_art) if a is not None]
        if handles:
            self._ax.legend(handles=handles, loc='upper right',
                            fontsize=8, framealpha=0.75)

        self.draw_idle()

    def clear_agents(self):
        for art in (self._agent_art, self._best_art):
            if art is not None:
                try:
                    art.remove()
                except Exception:
                    pass
        self._agent_art = None
        self._best_art = None
        self.draw_idle()

    # ------------------------------------------------------------------
    # Pheromone (ACO)
    # ------------------------------------------------------------------

    def update_pheromone(self, pheromone: np.ndarray, x_min, x_max, y_min, y_max, z_base=None):
        if pheromone is None or pheromone.ndim != 2:
            return
        self.clear_pheromone()

        import matplotlib.cm as mcm

        # Downsample to at most 30×30 for performance
        n_src = pheromone.shape[0]
        step = max(1, n_src // 30)
        ph = pheromone[::step, ::step]
        nh = ph.shape[0]

        xs = np.linspace(x_min, x_max, nh)
        ys = np.linspace(y_min, y_max, nh)
        XX, YY = np.meshgrid(xs, ys)

        # Use stored data z-min so the floor never drags the axis down
        if z_base is not None and np.isfinite(z_base):
            zz = float(z_base)
        elif self._z_data_min is not None:
            pad = (self._z_data_max - self._z_data_min) * 0.05 if self._z_data_max else 0.0
            zz = self._z_data_min - pad
        else:
            zz = 0.0
        Z_flat = np.full_like(XX, zz, dtype=float)

        pmin, pmax = ph.min(), ph.max()
        norm_p = (ph - pmin) / (pmax - pmin + 1e-12)

        cmap = mcm.get_cmap('YlOrRd')
        facecolors = cmap(norm_p)
        facecolors[..., 3] = 0.65  # alpha

        self._pheromone_art = self._ax.plot_surface(
            XX, YY, Z_flat,
            facecolors=facecolors,
            shade=False,
            linewidth=0,
            zorder=0,
        )
        self.draw_idle()

    def clear_pheromone(self):
        if self._pheromone_art is not None:
            try:
                self._pheromone_art.remove()
            except Exception:
                pass
            self._pheromone_art = None
        self.draw_idle()
