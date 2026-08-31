import json
from pathlib import Path

import pytest

from continuitytwin.engine import evaluate

ROOT = Path(__file__).parents[1]


@pytest.fixture
def scenario():
    return json.loads((ROOT / "examples/revenue-platform/game-day.json").read_text())


def test_recovery_order_respects_dependencies(scenario):
    order = evaluate(scenario)["recovery_order"]
    assert order.index("network") < order.index("postgresql") < order.index("decision-api") < order.index("frontend")


def test_zone_failover_meets_zero_rpo(scenario):
    experiment = evaluate(scenario)["experiments"][0]
    assert experiment["status"] == "pass"
    assert experiment["measured_rpo_seconds"] == 0


def test_region_failure_validates_business_transactions(scenario):
    experiment = evaluate(scenario)["experiments"][1]
    assert experiment["status"] == "pass"
    assert experiment["duplicate_transactions"] == 0
    assert experiment["missing_transactions"] == 0


def test_rpo_failure_blocks_restore_promotion(scenario):
    experiment = evaluate(scenario)["experiments"][2]
    assert experiment["status"] == "fail"
    assert "rpo" in experiment["failed_gates"]


def test_expected_value_is_probability_weighted(scenario):
    economics = evaluate(scenario)["unit_economics"]
    assert economics["risk_adjusted_outage_value_usd"] < economics["maximum_contribution_interruption_reduction_usd"]
    assert economics["maximum_exposure_is_not_annual_savings"]


def test_never_injects_or_promotes_automatically(scenario):
    control = evaluate(scenario)["production_control"]
    assert not control["auto_inject_failure"]
    assert not control["auto_promote_recovery"]


def test_receipt_is_deterministic(scenario):
    assert evaluate(scenario)["receipt_sha256"] == evaluate(scenario)["receipt_sha256"]


def test_cycle_fails_closed(scenario):
    scenario["dependencies"].append({"dependency": "frontend", "service": "dns"})
    with pytest.raises(ValueError):
        evaluate(scenario)
