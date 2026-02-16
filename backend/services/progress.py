"""실시간 분석 진행률 추적 모듈."""

_state = {"step": "idle", "percent": 0}


def update(step: str, percent: int):
    _state["step"] = step
    _state["percent"] = max(0, min(percent, 100))


def get():
    return _state.copy()


def reset():
    _state["step"] = "idle"
    _state["percent"] = 0
