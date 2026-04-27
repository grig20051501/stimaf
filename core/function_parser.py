import sympy as sp
import numpy as np
from sympy.utilities.lambdify import lambdify


class FunctionParser:
    _LOCAL_DICT = {
        'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
        'exp': sp.exp, 'log': sp.log, 'sqrt': sp.sqrt,
        'abs': sp.Abs, 'pi': sp.pi, 'e': sp.E,
        'sinh': sp.sinh, 'cosh': sp.cosh, 'tanh': sp.tanh,
        'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan,
        'atan2': sp.atan2,
    }

    def parse(self, expr_str: str):
        """
        Parse math string into a numpy callable.
        Returns (callable, variables, sympy_expr).
        Raises ValueError on any error.
        """
        x_sym = sp.Symbol('x')
        y_sym = sp.Symbol('y')
        local = dict(self._LOCAL_DICT)
        local['x'] = x_sym
        local['y'] = y_sym

        try:
            expr = sp.sympify(expr_str, locals=local)
        except (sp.SympifyError, SyntaxError, TypeError) as e:
            raise ValueError(f"Ошибка синтаксиса: {e}") from e

        free = expr.free_symbols
        unknown = free - {x_sym, y_sym}
        if unknown:
            names = ', '.join(sorted(str(s) for s in unknown))
            raise ValueError(f"Неизвестные переменные: {names}. Допустимы только x и y.")

        uses_y = y_sym in free
        variables = [x_sym, y_sym] if uses_y else [x_sym]

        try:
            func = lambdify(variables, expr, modules=[{'ImmutableMatrix': np.array}, 'numpy'])
        except Exception as e:
            raise ValueError(f"Не удалось скомпилировать функцию: {e}") from e

        return func, variables, expr

    def is_3d(self, variables) -> bool:
        return len(variables) == 2
