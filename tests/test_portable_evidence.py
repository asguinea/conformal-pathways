"""Only roundoff in interval endpoints may use the portable audit allowance."""

import math
import runpy
from pathlib import Path

import pytest

compare_value = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/verify_evidence_portable.py")
)["compare_value"]


def test_single_step_interval_roundoff_is_recorded():
    differences = []
    compare_value(0.9, math.nextafter(0.9, 1.0), "interval_low", differences)
    assert len(differences) == 1
    assert 0 < differences[0]["absolute_difference"] < 1e-15


@pytest.mark.parametrize("field", ["mean", "n_units", "observed_max", "alpha"])
def test_other_fields_require_exact_agreement(field):
    with pytest.raises(ValueError, match="Non-interval"):
        compare_value(0.9, math.nextafter(0.9, 1.0), field, [])


@pytest.mark.parametrize("actual", [None, "", float("nan"), float("inf"), True, 0.91])
def test_invalid_or_materially_changed_interval_fails(actual):
    with pytest.raises(ValueError):
        compare_value(0.9, actual, "interval_high", [])
