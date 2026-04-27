from dataclasses import dataclass
from typing import List, Callable, Tuple


PALETTE: List[Tuple[int, int, int]] = [
    (31, 119, 180),
    (255, 127, 14),
    (44, 160, 44),
    (214, 39, 40),
    (148, 103, 189),
    (140, 86, 75),
    (227, 119, 194),
    (127, 127, 127),
    (188, 189, 34),
    (23, 190, 207),
]


@dataclass
class FunctionEntry:
    name: str
    func: Callable
    variables: list
    color: Tuple[int, int, int]
    expr_str: str


class FunctionRegistry:
    def __init__(self):
        self._entries: List[FunctionEntry] = []
        self._color_idx: int = 0

    def add(self, expr_str: str, func: Callable, variables: list) -> FunctionEntry:
        color = PALETTE[self._color_idx % len(PALETTE)]
        self._color_idx += 1
        entry = FunctionEntry(
            name=expr_str,
            func=func,
            variables=variables,
            color=color,
            expr_str=expr_str,
        )
        self._entries.append(entry)
        return entry

    def remove(self, expr_str: str):
        self._entries = [e for e in self._entries if e.expr_str != expr_str]

    def clear(self):
        self._entries.clear()
        self._color_idx = 0

    @property
    def entries(self) -> List[FunctionEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)
