from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from typing import Any


def evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    _validate(scenario)
    order = _topological_order(scenario["services"], scenario["dependencies"])
    experiments = [_experiment(item, scenario, order) for item in scenario["experiments"]]
    passed = [item for item in experiments if item["status"] == "pass"]
    economics = _economics(scenario["economics"], experiments)
    report: dict[str, Any] = {
        "schema_version": "continuitytwin/v1",
        "scenario": scenario["scenario"],
        "evidence_level": "deterministic-synthetic-recovery-game-day",
        "recovery_order": order,
        "experiments": experiments,
        "scorecard": {
            "experiments": len(experiments),
            "passed": len(passed),
            "failed": len(experiments) - len(passed),
            "pass_rate_pct": round(len(passed) / len(experiments) * 100, 2),
            "worst_rto_minutes": max(item["measured_rto_minutes"] for item in experiments),
            "worst_rpo_seconds": max(item["measured_rpo_seconds"] for item in experiments),
        },
        "unit_economics": economics,
        "production_control": {
            "auto_inject_failure": False,
            "auto_promote_recovery": False,
            "required_gates": ["scope approval", "blast-radius limit", "abort condition", "transaction validation", "data reconciliation", "business owner approval"],
        },
        "claim_boundary": [
            "No Azure, AWS, GCP, Kubernetes, database, identity or production system failure was injected",
            "Timings, data loss, revenue, probability and recovery costs are synthetic inputs",
            "An experiment passes only as a modeled evidence contract, not as proof of a live recovery",
            "Maximum outage exposure is not represented as guaranteed annual savings",
        ],
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def _topological_order(services: list[dict[str, Any]], edges: list[dict[str, str]]) -> list[str]:
    names = {item["name"] for item in services}
    graph: dict[str, list[str]] = defaultdict(list)
    degree = {name: 0 for name in names}
    for edge in edges:
        dependency, service = edge["dependency"], edge["service"]
        if dependency not in names or service not in names:
            raise ValueError("dependency references unknown service")
        graph[dependency].append(service)
        degree[service] += 1
    queue = deque(sorted(name for name, value in degree.items() if value == 0))
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for child in sorted(graph[node]):
            degree[child] -= 1
            if degree[child] == 0:
                queue.append(child)
    if len(order) != len(names):
        raise ValueError("recovery dependency graph contains a cycle")
    return order


def _experiment(item: dict[str, Any], scenario: dict[str, Any], order: list[str]) -> dict[str, Any]:
    service_map = {service["name"]: service for service in scenario["services"]}
    affected = set(item["affected_services"])
    missing = affected - service_map.keys()
    if missing:
        raise ValueError(f"experiment references unknown services: {', '.join(sorted(missing))}")
    recovery_minutes = sum(service_map[name]["recovery_minutes"] for name in order if name in affected)
    measured_rto = item["detection_minutes"] + recovery_minutes + item["transaction_validation_minutes"] + item["backlog_recovery_minutes"]
    validations = item["transaction_validations"]
    transactions_pass = all(check["passed"] for check in validations)
    duplicate_count = sum(check["duplicates"] for check in validations)
    missing_count = sum(check["missing"] for check in validations)
    data_consistent = duplicate_count == 0 and missing_count == 0 and item["checksum_match"]
    rto_pass = measured_rto <= item["rto_target_minutes"]
    rpo_pass = item["measured_rpo_seconds"] <= item["rpo_target_seconds"]
    status = "pass" if all((transactions_pass, data_consistent, rto_pass, rpo_pass, item["rollback_verified"])) else "fail"
    return {
        "name": item["name"],
        "failure_type": item["failure_type"],
        "affected_services": item["affected_services"],
        "recovery_sequence": [name for name in order if name in affected],
        "measured_rto_minutes": measured_rto,
        "rto_target_minutes": item["rto_target_minutes"],
        "measured_rpo_seconds": item["measured_rpo_seconds"],
        "rpo_target_seconds": item["rpo_target_seconds"],
        "transaction_validations": validations,
        "duplicate_transactions": duplicate_count,
        "missing_transactions": missing_count,
        "checksum_match": item["checksum_match"],
        "rollback_verified": item["rollback_verified"],
        "status": status,
        "failed_gates": [name for name, passed in {"rto": rto_pass, "rpo": rpo_pass, "transactions": transactions_pass, "data-integrity": data_consistent, "rollback": item["rollback_verified"]}.items() if not passed],
    }


def _economics(values: dict[str, float], experiments: list[dict[str, Any]]) -> dict[str, Any]:
    validated_rto = max(item["measured_rto_minutes"] for item in experiments) / 60
    avoided_hours = max(0, values["baseline_outage_hours"] - validated_rto)
    maximum_interruption_reduction = avoided_hours * values["contribution_per_hour_usd"]
    risk_adjusted = maximum_interruption_reduction * values["annual_major_event_probability"]
    annual_value = risk_adjusted + values["engineering_capacity_value_usd"] + values["manual_dr_cost_avoided_usd"]
    return {
        "baseline_outage_hours": values["baseline_outage_hours"],
        "modeled_validated_rto_hours": round(validated_rto, 2),
        "maximum_contribution_interruption_reduction_usd": round(maximum_interruption_reduction, 2),
        "annual_major_event_probability": values["annual_major_event_probability"],
        "risk_adjusted_outage_value_usd": round(risk_adjusted, 2),
        "engineering_capacity_value_usd": values["engineering_capacity_value_usd"],
        "manual_dr_cost_avoided_usd": values["manual_dr_cost_avoided_usd"],
        "annual_platform_cost_usd": values["annual_platform_cost_usd"],
        "modeled_annual_net_value_usd": round(annual_value - values["annual_platform_cost_usd"], 2),
        "maximum_exposure_is_not_annual_savings": True,
    }


def _validate(scenario: dict[str, Any]) -> None:
    required = {"scenario", "services", "dependencies", "experiments", "economics"}
    missing = sorted(required - scenario.keys())
    if missing:
        raise ValueError(f"missing keys: {', '.join(missing)}")
    names = [item["name"] for item in scenario["services"]]
    if not names or len(names) != len(set(names)):
        raise ValueError("service names must be present and unique")
    if not scenario["experiments"]:
        raise ValueError("at least one experiment is required")
