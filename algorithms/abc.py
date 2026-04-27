import numpy as np
from .base import BaseSwarmAlgorithm


class ABC(BaseSwarmAlgorithm):
    """Artificial Bee Colony optimisation algorithm."""

    def __init__(self, func, bounds: list, n_bees: int = 40,
                 limit: int = None, max_iter: int = 100):
        super().__init__(func, bounds, max_iter)
        self.n_bees = n_bees
        self.n_employed = max(1, n_bees // 2)
        # if limit not set, use a common heuristic
        self.limit = limit if limit is not None else self.n_employed * len(bounds)
        self._init_colony()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_colony(self):
        dim = len(self.bounds)
        self._dim = dim
        self._lo = np.array([b[0] for b in self.bounds], dtype=float)
        self._hi = np.array([b[1] for b in self.bounds], dtype=float)

        self.sources = (
            self._lo + np.random.rand(self.n_employed, dim) * (self._hi - self._lo)
        )
        self.source_values = np.array([self._eval(s) for s in self.sources])
        self.trial_counts = np.zeros(self.n_employed, dtype=int)

        best_idx = int(np.argmin(self.source_values))
        self._best_position = self.sources[best_idx].copy()
        self._best_value = float(self.source_values[best_idx])

        self._all_positions = self.sources.copy()
        self._history = []
        self.current_iter = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _eval(self, pos: np.ndarray) -> float:
        try:
            val = self.func(*pos) if self._dim > 1 else self.func(pos[0])
            return float(val)
        except Exception:
            return float('inf')

    def _fitness(self, val: float) -> float:
        return 1.0 / (1.0 + val) if val >= 0 else 1.0 + abs(val)

    def _explore(self, i: int) -> np.ndarray:
        """Generate a neighbour of source i."""
        # pick a random different source
        candidates = [k for k in range(self.n_employed) if k != i]
        k = candidates[np.random.randint(len(candidates))]
        j = np.random.randint(self._dim)
        phi = np.random.uniform(-1.0, 1.0)

        candidate = self.sources[i].copy()
        candidate[j] += phi * (self.sources[i][j] - self.sources[k][j])
        return np.clip(candidate, self._lo, self._hi)

    def _greedy_update(self, i: int, candidate: np.ndarray):
        """Greedy selection: keep candidate if better."""
        cval = self._eval(candidate)
        if cval < self.source_values[i]:
            self.sources[i] = candidate
            self.source_values[i] = cval
            self.trial_counts[i] = 0
            if cval < self._best_value:
                self._best_value = cval
                self._best_position = candidate.copy()
        else:
            self.trial_counts[i] += 1

    # ------------------------------------------------------------------
    # Algorithm phases
    # ------------------------------------------------------------------

    def step(self) -> dict:
        if self.current_iter >= self.max_iter:
            return self._make_state()

        onlooker_positions = np.empty_like(self.sources)

        # 1. Employed bee phase
        for i in range(self.n_employed):
            self._greedy_update(i, self._explore(i))

        # 2. Onlooker bee phase
        fitnesses = np.array([self._fitness(v) for v in self.source_values])
        total_fit = fitnesses.sum()
        probs = fitnesses / total_fit if total_fit > 0 else np.ones(self.n_employed) / self.n_employed

        for o in range(self.n_employed):
            i = int(np.random.choice(self.n_employed, p=probs))
            candidate = self._explore(i)
            onlooker_positions[o] = candidate
            self._greedy_update(i, candidate)

        # 3. Scout bee phase
        for i in range(self.n_employed):
            if self.trial_counts[i] >= self.limit:
                self.sources[i] = (
                    self._lo + np.random.rand(self._dim) * (self._hi - self._lo)
                )
                self.source_values[i] = self._eval(self.sources[i])
                self.trial_counts[i] = 0

        self._all_positions = np.vstack([self.sources, onlooker_positions])
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
            'positions': self._all_positions.copy(),
            'best_position': self._best_position.copy(),
            'best_value': self._best_value,
        }

    @property
    def best_position(self) -> np.ndarray:
        return self._best_position.copy()

    @property
    def best_value(self) -> float:
        return self._best_value
