import numpy as np
from .base import BaseSwarmAlgorithm


class ACO(BaseSwarmAlgorithm):
    """Continuous ACO on a discretized grid with rank-based pheromone updates."""

    def __init__(self, func, bounds: list, n_ants: int = 30,
                 evaporation: float = 0.5, alpha: float = 1.0, beta: float = 2.0,
                 grid_resolution: int = 50, max_iter: int = 100):
        super().__init__(func, bounds, max_iter)
        self.n_ants = n_ants
        self.evaporation = evaporation
        self.alpha = alpha
        self.beta = beta
        self.grid_resolution = grid_resolution
        self._init_colony()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_colony(self):
        self._lo = np.array([b[0] for b in self.bounds], dtype=float)
        self._hi = np.array([b[1] for b in self.bounds], dtype=float)
        self._dim = len(self.bounds)
        self._grid_shape = tuple(self.grid_resolution for _ in range(self._dim))

        self._axes = [
            np.linspace(self._lo[d], self._hi[d], self.grid_resolution)
            for d in range(self._dim)
        ]

        self.pheromone = np.ones(self._grid_shape, dtype=float)
        self._heuristic = self._precompute_heuristic()

        self._best_position: np.ndarray = None
        self._best_value: float = float('inf')
        self.ant_positions: np.ndarray = None
        self._history = []
        self.current_iter = 0

    # ------------------------------------------------------------------
    # Heuristic (precomputed, static)
    # ------------------------------------------------------------------

    def _precompute_heuristic(self) -> np.ndarray:
        """
        η(i) ∝ quality of grid cell i for minimisation.
        Lower f → higher η. Uses rank-normalised inverse distance to minimum.
        """
        vals = np.zeros(self._grid_shape, dtype=float)
        for idx in np.ndindex(*self._grid_shape):
            vals[idx] = self._eval_pos(self._idx_to_pos(idx))

        finite = np.isfinite(vals)
        if not finite.any():
            return np.ones(self._grid_shape, dtype=float)

        f_min = vals[finite].min()
        f_max = vals[finite].max()
        span = f_max - f_min

        if span < 1e-12:
            return np.ones(self._grid_shape, dtype=float)

        # h = (f_max - f) / span  →  1.0 at minimum, 0.0 at maximum
        h = (f_max - vals) / span
        h = np.clip(h, 0.0, 1.0)
        h[~finite] = 0.0
        # floor so every cell has some chance of being visited
        h = h * 0.99 + 0.01
        return h

    # ------------------------------------------------------------------
    # Grid helpers
    # ------------------------------------------------------------------

    def _idx_to_pos(self, idx) -> np.ndarray:
        return np.array([self._axes[d][idx[d]] for d in range(self._dim)])

    def _eval_pos(self, pos: np.ndarray) -> float:
        try:
            val = self.func(*pos) if self._dim > 1 else self.func(pos[0])
            return float(val)
        except Exception:
            return float('inf')

    # ------------------------------------------------------------------
    # Probability
    # ------------------------------------------------------------------

    def _probabilities(self) -> np.ndarray:
        scores = (self.pheromone ** self.alpha) * (self._heuristic ** self.beta)
        total = scores.sum()
        if total <= 0 or not np.isfinite(total):
            return np.ones(scores.size, dtype=float) / scores.size
        return (scores / total).ravel()

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self) -> dict:
        if self.current_iter >= self.max_iter:
            return self._make_state()

        probs = self._probabilities()
        flat_indices = np.random.choice(probs.size, size=self.n_ants, p=probs)

        positions = []
        values = []
        for fi in flat_indices:
            idx = np.unravel_index(fi, self._grid_shape)
            pos = self._idx_to_pos(idx)
            val = self._eval_pos(pos)
            positions.append(pos)
            values.append(val)
            if val < self._best_value:
                self._best_value = val
                self._best_position = pos.copy()

        self.ant_positions = np.array(positions)
        v_arr = np.array(values, dtype=float)

        # Pheromone evaporation
        self.pheromone *= (1.0 - self.evaporation)

        # Rank-based deposit: best ant (lowest f) deposits ~1.0, worst ~0.0
        finite_mask = np.isfinite(v_arr)
        if finite_mask.any():
            v_min = v_arr[finite_mask].min()
            v_max = v_arr[finite_mask].max()
            span = v_max - v_min

            for fi, val in zip(flat_indices, v_arr):
                idx = np.unravel_index(fi, self._grid_shape)
                if not np.isfinite(val):
                    quality = 0.0
                elif span < 1e-12:
                    quality = 1.0
                else:
                    quality = (v_max - val) / span   # 1.0 = best, 0.0 = worst
                self.pheromone[idx] += quality * 0.9 + 0.1   # floor keeps exploration

        self.pheromone = np.clip(self.pheromone, 1e-6, 1e6)

        self.current_iter += 1
        state = self._make_state()
        self._history.append(state)
        return state

    def run(self) -> dict:
        while self.current_iter < self.max_iter:
            self.step()
        return self._make_state()

    def reset(self):
        self._init_colony()

    def _make_state(self) -> dict:
        return {
            'iteration': self.current_iter,
            'positions': self.ant_positions.copy() if self.ant_positions is not None
                         else np.zeros((0, self._dim)),
            'best_position': self._best_position.copy() if self._best_position is not None
                             else np.zeros(self._dim),
            'best_value': self._best_value,
            'pheromone': self.pheromone.copy(),
            'axes': self._axes,
        }

    @property
    def best_position(self) -> np.ndarray:
        return self._best_position.copy() if self._best_position is not None \
               else np.zeros(self._dim)

    @property
    def best_value(self) -> float:
        return self._best_value
