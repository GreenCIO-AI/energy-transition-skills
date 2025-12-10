#!/usr/bin/env python3
"""
LCOE Sensitivity Analysis

Analyzes how LCOE changes when varying key input parameters.
Useful for understanding project risk and identifying critical assumptions.

Usage:
    python sensitivity_analysis.py --input project.json --vary discount_rate
    python sensitivity_analysis.py --input project.json --vary capex_usd --range 0.8,1.2,0.1
    python sensitivity_analysis.py --input project.json --all

No external dependencies - uses only Python standard library.
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from calculate_lcoe import validate_input, calculate_lcoe, LCOEInput

VERSION = "1.0.0"
SKILL_NAME = "lcoe-calculator"

# Default variation ranges (as multipliers for most, absolute for rates)
DEFAULT_RANGES = {
    "capex_usd": {"min": 0.7, "max": 1.3, "step": 0.1, "type": "multiplier"},
    "annual_opex_usd": {"min": 0.7, "max": 1.3, "step": 0.1, "type": "multiplier"},
    "annual_fuel_cost_usd": {"min": 0.7, "max": 1.3, "step": 0.1, "type": "multiplier"},
    "annual_generation_mwh": {"min": 0.8, "max": 1.2, "step": 0.05, "type": "multiplier"},
    "project_lifetime_years": {"min": 15, "max": 35, "step": 5, "type": "absolute"},
    "discount_rate": {"min": 0.04, "max": 0.14, "step": 0.02, "type": "absolute"},
    "degradation_rate": {"min": 0.0, "max": 0.02, "step": 0.005, "type": "absolute"},
    "opex_escalation_rate": {"min": 0.0, "max": 0.05, "step": 0.01, "type": "absolute"},
    "fuel_escalation_rate": {"min": 0.0, "max": 0.05, "step": 0.01, "type": "absolute"},
}


def generate_range(
    base_value: float,
    param_name: str,
    custom_range: Optional[str] = None
) -> List[float]:
    """Generate a range of values for sensitivity analysis."""
    if custom_range:
        parts = custom_range.split(",")
        if len(parts) == 3:
            min_val, max_val, step = float(parts[0]), float(parts[1]), float(parts[2])
            values = []
            current = min_val
            while current <= max_val + 0.0001:  # Small epsilon for float comparison
                values.append(round(current, 6))
                current += step
            return values
        else:
            # Treat as list of values
            return [float(x.strip()) for x in parts]

    # Use default ranges
    if param_name not in DEFAULT_RANGES:
        # Default to ±30% with 10% steps
        return [base_value * m for m in [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]]

    config = DEFAULT_RANGES[param_name]
    if config["type"] == "multiplier":
        return [
            round(base_value * m, 2)
            for m in [
                config["min"],
                config["min"] + config["step"],
                config["min"] + 2 * config["step"],
                1.0,
                config["max"] - 2 * config["step"],
                config["max"] - config["step"],
                config["max"]
            ]
        ]
    else:
        # Absolute values
        values = []
        current = config["min"]
        while current <= config["max"] + 0.0001:
            values.append(round(current, 6))
            current += config["step"]
        return values


def run_sensitivity(
    base_inputs: LCOEInput,
    param_name: str,
    values: List[float]
) -> Dict[str, Any]:
    """Run sensitivity analysis for a single parameter."""
    base_result = calculate_lcoe(base_inputs)
    base_lcoe = base_result["lcoe_usd_per_mwh"]
    base_value = base_inputs.get(param_name, 0)

    results = []
    for value in values:
        # Create modified inputs
        modified = dict(base_inputs)
        modified[param_name] = value

        # Handle integer types
        if param_name == "project_lifetime_years":
            modified[param_name] = int(value)

        # Validate and calculate
        validated = validate_input(modified)
        if "code" in validated:
            # Skip invalid configurations
            continue

        result = calculate_lcoe(validated)
        lcoe = result["lcoe_usd_per_mwh"]

        # Calculate percent change
        pct_change = ((lcoe - base_lcoe) / base_lcoe * 100) if base_lcoe > 0 else 0
        value_pct_change = ((value - base_value) / base_value * 100) if base_value > 0 else 0

        results.append({
            "value": value,
            "value_pct_change": round(value_pct_change, 2),
            "lcoe_usd_per_mwh": lcoe,
            "lcoe_pct_change": round(pct_change, 2),
            "is_base": abs(value - base_value) < 0.0001
        })

    # Calculate elasticity (% change in LCOE / % change in parameter)
    # Using average of non-base values
    elasticities = []
    for r in results:
        if not r["is_base"] and r["value_pct_change"] != 0:
            elasticities.append(r["lcoe_pct_change"] / r["value_pct_change"])

    avg_elasticity = sum(elasticities) / len(elasticities) if elasticities else 0

    return {
        "parameter": param_name,
        "base_value": base_value,
        "base_lcoe_usd_per_mwh": base_lcoe,
        "elasticity": round(avg_elasticity, 3),
        "elasticity_interpretation": interpret_elasticity(avg_elasticity),
        "values_tested": len(results),
        "min_lcoe": min(r["lcoe_usd_per_mwh"] for r in results) if results else 0,
        "max_lcoe": max(r["lcoe_usd_per_mwh"] for r in results) if results else 0,
        "lcoe_range": round(
            max(r["lcoe_usd_per_mwh"] for r in results) -
            min(r["lcoe_usd_per_mwh"] for r in results), 2
        ) if results else 0,
        "results": results
    }


def interpret_elasticity(elasticity: float) -> str:
    """Provide interpretation of elasticity value."""
    abs_e = abs(elasticity)
    if abs_e < 0.1:
        return "Negligible impact - LCOE is insensitive to this parameter"
    elif abs_e < 0.5:
        return "Low impact - modest changes in LCOE"
    elif abs_e < 1.0:
        return "Moderate impact - significant influence on LCOE"
    else:
        return "High impact - critical parameter that strongly affects LCOE"


def run_full_sensitivity(base_inputs: LCOEInput) -> Dict[str, Any]:
    """Run sensitivity analysis on all key parameters."""
    params_to_analyze = [
        "capex_usd",
        "annual_opex_usd",
        "annual_generation_mwh",
        "project_lifetime_years",
        "discount_rate",
        "degradation_rate"
    ]

    # Only include fuel if it's non-zero
    if base_inputs.get("annual_fuel_cost_usd", 0) > 0:
        params_to_analyze.append("annual_fuel_cost_usd")
        params_to_analyze.append("fuel_escalation_rate")

    if base_inputs.get("annual_opex_usd", 0) > 0:
        params_to_analyze.append("opex_escalation_rate")

    all_results = {}
    for param in params_to_analyze:
        base_value = base_inputs.get(param, 0)
        if param in base_inputs or base_value > 0:
            values = generate_range(base_value, param)
            all_results[param] = run_sensitivity(base_inputs, param, values)

    # Rank parameters by impact
    ranked = sorted(
        [
            {"parameter": k, "elasticity": abs(v["elasticity"]), "lcoe_range": v["lcoe_range"]}
            for k, v in all_results.items()
        ],
        key=lambda x: x["elasticity"],
        reverse=True
    )

    return {
        "summary": {
            "parameters_analyzed": len(all_results),
            "most_sensitive_parameter": ranked[0]["parameter"] if ranked else None,
            "parameter_ranking": ranked
        },
        "by_parameter": all_results
    }


def main():
    parser = argparse.ArgumentParser(
        description="LCOE Sensitivity Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single parameter with default range
  python sensitivity_analysis.py --input project.json --vary discount_rate

  # Custom range (min,max,step)
  python sensitivity_analysis.py --input project.json --vary capex_usd --range 0.7,1.3,0.1

  # Full sensitivity analysis
  python sensitivity_analysis.py --input project.json --all
        """
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Input JSON file with base project parameters"
    )
    parser.add_argument(
        "--vary", "-v",
        type=str,
        help="Parameter to vary"
    )
    parser.add_argument(
        "--range", "-r",
        type=str,
        help="Range specification: min,max,step or comma-separated values"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run full sensitivity analysis on all parameters"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print output"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.vary and not args.all:
        parser.error("Either --vary or --all must be specified")

    # Read input
    try:
        with open(args.input, "r") as f:
            input_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        output = {
            "success": False,
            "error": {
                "code": "INPUT_ERROR",
                "message": str(e)
            }
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)

    # Validate base inputs
    validated = validate_input(input_data)
    if "code" in validated:
        output = {
            "success": False,
            "error": validated
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)

    # Run analysis
    if args.all:
        results = run_full_sensitivity(validated)
    else:
        base_value = validated.get(args.vary, 0)
        values = generate_range(base_value, args.vary, args.range)
        results = run_sensitivity(validated, args.vary, values)

    # Build output
    output = {
        "success": True,
        "analysis_type": "full" if args.all else "single_parameter",
        "data": results,
        "metadata": {
            "skill": SKILL_NAME,
            "version": VERSION,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
    }

    result_json = json.dumps(output, indent=2 if args.pretty else None)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result_json)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
