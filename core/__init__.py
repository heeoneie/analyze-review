"""Core AI analysis package for e-commerce review analysis.

`ReviewAnalyzer` 와 `DataLoader` 는 지연 임포트한다. 둘 다 pandas·kagglehub 를
끌어오는데, 답글 생성만 배포하는 슬림 컨테이너에는 그 의존성이 없기 때문이다.
`from core import ReviewAnalyzer` 같은 기존 사용법은 그대로 동작한다.
"""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # 정적 분석기가 __all__ 의 이름을 찾을 수 있게 한다
    from core.analyzer import ReviewAnalyzer
    from core.data_loader import DataLoader

__all__ = ["ReviewAnalyzer", "DataLoader"]

_LAZY = {
    "ReviewAnalyzer": ("core.analyzer", "ReviewAnalyzer"),
    "DataLoader": ("core.data_loader", "DataLoader"),
}


def __getattr__(name):
    if name in _LAZY:
        module_name, attr = _LAZY[name]
        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals()) + __all__)
