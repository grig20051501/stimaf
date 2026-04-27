import numpy as np
from .base import BaseSwarmAlgorithm


class PSO(BaseSwarmAlgorithm):
    def __init__(self, func, bounds: list, n_particles: int = 30,
                 inertia: float = 0.7, cognitive: float = 1.5, social: float = 1.5,
                 max_iter: int = 100):
        super().__init__(func, bounds, max_iter)
        self.n_particles = n_particles
        self.inertia = inertia
        self.cognitive = cognitive
        self.social = social
        self._init_swarm()

    def _init_swarm(self):
        dim = len(self.bounds)
        lo = np.array([b[0] for b in self.bounds], dtype=float)
        hi = np.array([b[1] for b in self.bounds], dtype=float)
        self._lo = lo
        self._hi = hi

        self.positions = lo + np.random.rand(self.n_particles, dim) * (hi - lo)
        span = hi - lo
        self.velocities = -span + np.random.rand(self.n_particles, dim) * 2 * span
        self.personal_best = self.positions.copy()
        self.personal_best_values = np.array([self._eval(p) for p in self.positions])

        best_idx = int(np.argmin(self.personal_best_values))
        self._best_position = self.personal_best[best_idx].copy()
        self._best_value = float(self.personal_best_values[best_idx])
        self._history = []
        self.current_iter = 0

    def _eval(self, pos: np.ndarray) -> float:
        try:
            val = self.func(*pos) if len(pos) > 1 else self.func(pos[0])
            return float(val)
        except Exception:
            return float('inf')

    def step(self) -> dict:
        if self.current_iter >= self.max_iter:
            return self._make_state()

        r1 = np.random.rand(self.n_particles, len(self.bounds))
        r2 = np.random.rand(self.n_particles, len(self.bounds))

        self.velocities = (
            self.inertia * self.velocities
            + self.cognitive * r1 * (self.personal_best - self.positions)
            + self.social * r2 * (self._best_position - self.positions)
        )
        self.positions = np.clip(self.positions + self.velocities, self._lo, self._hi)

        values = np.array([self._eval(p) for p in self.positions])
        mask = values < self.personal_best_values
        self.personal_best[mask] = self.positions[mask].copy()
        self.personal_best_values[mask] = values[mask]

        best_idx = int(np.argmin(self.personal_best_values))
        if self.personal_best_values[best_idx] < self._best_value:
            self._best_value = float(self.personal_best_values[best_idx])
            self._best_position = self.personal_best[best_idx].copy()

        self.current_iter += 1
        state = self._make_state()
        self._history.append(state)
        return state

    def run(self) -> dict:
        while self.current_iter < self.max_iter:
            self.step()
        return self._make_state()

    def reset(self):
        self._init_swarm()

    def _make_state(self) -> dict:
        return {
            'iteration': self.current_iter,
            'positions': self.positions.copy(),
            'best_position': self._best_position.copy(),
            'best_value': self._best_value,
        }

    @property
    def best_position(self) -> np.ndarray:
        return self._best_position.copy()

    @property
    def best_value(self) -> float:
        return self._best_value
