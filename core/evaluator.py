import numpy as np


class Evaluator:
    def __init__(self, resolution: int = 300):
        self.resolution = resolution

    def evaluate_2d(self, func, x_min: float, x_max: float):
        """Returns (x_arr, y_arr) for a 1-variable function."""
        x = np.linspace(x_min, x_max, self.resolution)
        try:
            y = np.asarray(func(x), dtype=float)
        except Exception:
            y = np.full(self.resolution, np.nan)
        y = np.where(np.isfinite(y), y, np.nan)
        return x, y

    def evaluate_3d(self, func, x_min: float, x_max: float, y_min: float, y_max: float,
                    resolution: int = None):
        """Returns (X, Y, Z) meshgrid for a 2-variable function."""
        res = resolution if resolution is not None else min(self.resolution, 150)
        x = np.linspace(x_min, x_max, res)
        y = np.linspace(y_min, y_max, res)
        X, Y = np.meshgrid(x, y)
        try:
            Z = np.asarray(func(X, Y), dtype=float)
        except Exception:
            Z = np.full_like(X, np.nan)
        Z = np.where(np.isfinite(Z), Z, np.nan)
        return X, Y, Z
