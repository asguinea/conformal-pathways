"""Result-aware sessions and an offline, explicitly simulated evaluation protocol."""

from .calibration import calibrate
from .engine import ScoreConfig, SequentialSession, StageFilter, select_action
from .evaluation import evaluate_sequential
from .simulation import DiagnosticScenario, proxy_scenarios

__all__ = [
    "DiagnosticScenario",
    "ScoreConfig",
    "SequentialSession",
    "StageFilter",
    "calibrate",
    "evaluate_sequential",
    "proxy_scenarios",
    "select_action",
]
