from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseSwarmAlgorithm(ABC):
    def __init__(self, func, bounds: list, max_iter: int):
        self.func = func
        self.bounds = bounds          # list of (lo, hi) per dimension
        self.max_iter = max_iter
        self.current_iter: int = 0
        self._history: List[dict] = []

    @abstractmethod
    def step(self) -> dict:
        """One iteration. Returns state dict with positions, best_position, best_value."""

    @abstractmethod
    def run(self) -> dict:
        """Full run."""

    @abstractmethod
    def reset(self):
        """Reset to initial state."""

    def get_history(self) -> List[dict]:
        return list(self._history)

    @property
    @abstractmethod
    def best_position(self) -> np.ndarray:
        ...

    @property
    @abstractmethod
    def best_value(self) -> float:
        ...
