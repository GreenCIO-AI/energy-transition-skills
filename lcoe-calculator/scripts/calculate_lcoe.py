#!/usr/bin/env python3
"""
LCOE Calculator - Levelized Cost of Energy

Calculates the levelized cost of energy for power generation projects
using industry-standard NREL/IEA methodology.

Usage:
    python calculate_lcoe.py < input.json > output.json
    python calculate_lcoe.py --input input.json --output output.json
    python calculate_lcoe.py --help

No external dependencies - uses only Python standard library.
"""

import json
import sys
import argparse
import hashlib
from datetime import datetime, timezone
from typing import TypedDict, Optional, List, Dict, Any, Union

# Version
VERSION = "1.0.0"
SKILL_NAME = "lcoe-calculator"


# ============================================================================
# Type Definitions
# ============================================================================

class LCOEInput(TypedDict, total=False):
    """Input parameters for LCOE calculation."""
    # Required
    capex_usd: float
    annual_generation_mwh: float
    project_lifetime_years: int
    discount_rate: float
    # Optional
    annual_opex_usd: float
    annual_fuel_cost_usd: float
    opex_escalation_rate: float
    fuel_escalation_rate: float
    degradation_rate: float
    capacity_mw: Optional[float]
    technology: str


class AnnualBreakdown(TypedDict):
    """Annual cost and generation breakdown."""
    year: int
    generation_mwh: float
    opex_usd: float
    fuel_usd: float
    total_cost_usd: float
    discounted_cost_usd: float
    discounted_generation_mwh: float
    cumulative_discounted_cost_usd: float
    cumulative_discounted_generation_mwh: float


class LCOEResult(TypedDict):
    """LCOE calculation results."""
    lcoe_usd_per_mwh: float
    lcoe_usd_per_kwh: float
    lcoe_cents_per_kwh: float
    total_lifecycle_cost_usd: float
    total_lifetime_generation_mwh: float
    npv_costs_usd: float
    npv_generation_mwh: float
    capacity_factor: Optional[float]
    annual_breakdown: List[AnnualBreakdown]
    inputs_summary: Dict[str, Any]


class ValidationError(TypedDict):
    """Validation error structure."""
    code: str
    message: str
    field: str
    received: Any
    expected: str


class LCOEOutput(TypedDict):
    """Complete output structure."""
    success: bool
    data: Optional[LCOEResult]
    error: Optional[ValidationError]
    metadata: Dict[str, Any]


# ============================================================================
# Validation
# ============================================================================

def validate_input(data: Dict[str, Any]) -> Union[LCOEInput, ValidationError]:
    """
    Validate input parameters.

    Returns validated LCOEInput or ValidationError.
    """
    errors: List[ValidationError] = []

    # Required fields
    required_fields = [
        ("capex_usd", "Capital expenditure in USD"),
        ("annual_generation_mwh", "Annual generation in MWh"),
        ("project_lifetime_years", "Project lifetime in years"),
        ("discount_rate", "Discount rate (decimal)")
    ]

    for field, desc in required_fields:
        if field not in data:
            return {
                "code": "MISSING_REQUIRED_FIELD",
                "message": f"Missing required field: {desc}",
                "field": field,
                "received": None,
                "expected": f"{field} is required"
            }

    # Validate capex_usd
    capex = data.get("capex_usd")
    if not isinstance(capex, (int, float)) or capex <= 0:
        return {
            "code": "INVALID_CAPEX",
            "message": "Capital expenditure must be a positive number",
            "field": "capex_usd",
            "received": capex,
            "expected": "> 0"
        }

    # Validate annual_generation_mwh
    gen = data.get("annual_generation_mwh")
    if not isinstance(gen, (int, float)) or gen <= 0:
        return {
            "code": "INVALID_GENERATION",
            "message": "Annual generation must be a positive number",
            "field": "annual_generation_mwh",
            "received": gen,
            "expected": "> 0"
        }

    # Validate project_lifetime_years
    lifetime = data.get("project_lifetime_years")
    if not isinstance(lifetime, int) or lifetime < 1 or lifetime > 50:
        return {
            "code": "INVALID_LIFETIME",
            "message": "Project lifetime must be between 1 and 50 years",
            "field": "project_lifetime_years",
            "received": lifetime,
            "expected": "1-50"
        }

    # Validate discount_rate
    rate = data.get("discount_rate")
    if not isinstance(rate, (int, float)) or rate < 0 or rate > 0.30:
        return {
            "code": "INVALID_DISCOUNT_RATE",
            "message": "Discount rate must be between 0 and 0.30 (0-30%)",
            "field": "discount_rate",
            "received": rate,
            "expected": "0-0.30"
        }

    # Validate optional fields
    opex = data.get("annual_opex_usd", 0)
    if not isinstance(opex, (int, float)) or opex < 0:
        return {
            "code": "INVALID_OPEX",
            "message": "Annual OPEX must be non-negative",
            "field": "annual_opex_usd",
            "received": opex,
            "expected": ">= 0"
        }

    fuel = data.get("annual_fuel_cost_usd", 0)
    if not isinstance(fuel, (int, float)) or fuel < 0:
        return {
            "code": "INVALID_FUEL_COST",
            "message": "Annual fuel cost must be non-negative",
            "field": "annual_fuel_cost_usd",
            "received": fuel,
            "expected": ">= 0"
        }

    opex_esc = data.get("opex_escalation_rate", 0.02)
    if not isinstance(opex_esc, (int, float)) or opex_esc < 0 or opex_esc > 0.20:
        return {
            "code": "INVALID_OPEX_ESCALATION",
            "message": "OPEX escalation rate must be between 0 and 0.20",
            "field": "opex_escalation_rate",
            "received": opex_esc,
            "expected": "0-0.20"
        }

    fuel_esc = data.get("fuel_escalation_rate", 0.02)
    if not isinstance(fuel_esc, (int, float)) or fuel_esc < 0 or fuel_esc > 0.20:
        return {
            "code": "INVALID_FUEL_ESCALATION",
            "message": "Fuel escalation rate must be between 0 and 0.20",
            "field": "fuel_escalation_rate",
            "received": fuel_esc,
            "expected": "0-0.20"
        }

    deg = data.get("degradation_rate", 0.005)
    if not isinstance(deg, (int, float)) or deg < 0 or deg > 0.10:
        return {
            "code": "INVALID_DEGRADATION",
            "message": "Degradation rate must be between 0 and 0.10",
            "field": "degradation_rate",
            "received": deg,
            "expected": "0-0.10"
        }

    # Build validated input with defaults
    validated: LCOEInput = {
        "capex_usd": float(capex),
        "annual_generation_mwh": float(gen),
        "project_lifetime_years": int(lifetime),
        "discount_rate": float(rate),
        "annual_opex_usd": float(opex),
        "annual_fuel_cost_usd": float(fuel),
        "opex_escalation_rate": float(opex_esc),
        "fuel_escalation_rate": float(fuel_esc),
        "degradation_rate": float(deg),
        "capacity_mw": data.get("capacity_mw"),
        "technology": data.get("technology", "generic")
    }

    return validated


# ============================================================================
# LCOE Calculation
# ============================================================================

def calculate_lcoe(inputs: LCOEInput) -> LCOEResult:
    """
    Calculate Levelized Cost of Energy.

    LCOE = NPV(Total Costs) / NPV(Total Generation)

    Where:
    - NPV(Costs) = CAPEX + Σ(O&M_t + Fuel_t) / (1+r)^t
    - NPV(Generation) = Σ(E_t) / (1+r)^t
    """
    capex = inputs["capex_usd"]
    base_generation = inputs["annual_generation_mwh"]
    lifetime = inputs["project_lifetime_years"]
    discount_rate = inputs["discount_rate"]
    base_opex = inputs["annual_opex_usd"]
    base_fuel = inputs["annual_fuel_cost_usd"]
    opex_escalation = inputs["opex_escalation_rate"]
    fuel_escalation = inputs["fuel_escalation_rate"]
    degradation = inputs["degradation_rate"]
    capacity = inputs.get("capacity_mw")

    # Initialize accumulators
    annual_breakdown: List[AnnualBreakdown] = []
    total_lifecycle_cost = capex  # Start with CAPEX
    total_generation = 0.0
    npv_costs = capex  # CAPEX is at year 0, no discounting
    npv_generation = 0.0

    cumulative_discounted_cost = capex
    cumulative_discounted_gen = 0.0

    # Calculate year-by-year
    for year in range(1, lifetime + 1):
        # Generation with degradation
        # Year 1 has no degradation, subsequent years degrade
        generation = base_generation * ((1 - degradation) ** (year - 1))

        # Costs with escalation
        opex = base_opex * ((1 + opex_escalation) ** (year - 1))
        fuel = base_fuel * ((1 + fuel_escalation) ** (year - 1))
        total_cost = opex + fuel

        # Discount factor
        discount_factor = (1 + discount_rate) ** year

        # Discounted values
        discounted_cost = total_cost / discount_factor
        discounted_gen = generation / discount_factor

        # Accumulate
        total_lifecycle_cost += total_cost
        total_generation += generation
        npv_costs += discounted_cost
        npv_generation += discounted_gen
        cumulative_discounted_cost += discounted_cost
        cumulative_discounted_gen += discounted_gen

        annual_breakdown.append({
            "year": year,
            "generation_mwh": round(generation, 2),
            "opex_usd": round(opex, 2),
            "fuel_usd": round(fuel, 2),
            "total_cost_usd": round(total_cost, 2),
            "discounted_cost_usd": round(discounted_cost, 2),
            "discounted_generation_mwh": round(discounted_gen, 2),
            "cumulative_discounted_cost_usd": round(cumulative_discounted_cost, 2),
            "cumulative_discounted_generation_mwh": round(cumulative_discounted_gen, 2)
        })

    # Calculate LCOE
    lcoe_per_mwh = npv_costs / npv_generation if npv_generation > 0 else 0
    lcoe_per_kwh = lcoe_per_mwh / 1000

    # Calculate capacity factor if capacity provided
    capacity_factor = None
    if capacity and capacity > 0:
        # Capacity factor = Actual Generation / (Capacity * Hours in Year)
        hours_per_year = 8760
        max_generation = capacity * hours_per_year
        capacity_factor = (base_generation / max_generation) * 100  # as percentage

    return {
        "lcoe_usd_per_mwh": round(lcoe_per_mwh, 2),
        "lcoe_usd_per_kwh": round(lcoe_per_kwh, 5),
        "lcoe_cents_per_kwh": round(lcoe_per_kwh * 100, 2),
        "total_lifecycle_cost_usd": round(total_lifecycle_cost, 2),
        "total_lifetime_generation_mwh": round(total_generation, 2),
        "npv_costs_usd": round(npv_costs, 2),
        "npv_generation_mwh": round(npv_generation, 2),
        "capacity_factor": round(capacity_factor, 1) if capacity_factor else None,
        "annual_breakdown": annual_breakdown,
        "inputs_summary": {
            "technology": inputs.get("technology", "generic"),
            "capacity_mw": capacity,
            "capex_usd": capex,
            "annual_opex_usd": base_opex,
            "annual_fuel_cost_usd": base_fuel,
            "annual_generation_mwh": base_generation,
            "project_lifetime_years": lifetime,
            "discount_rate": discount_rate,
            "opex_escalation_rate": opex_escalation,
            "fuel_escalation_rate": fuel_escalation,
            "degradation_rate": degradation
        }
    }


# ============================================================================
# Main Entry Point
# ============================================================================

def create_output(
    success: bool,
    data: Optional[LCOEResult] = None,
    error: Optional[ValidationError] = None,
    inputs_hash: str = ""
) -> LCOEOutput:
    """Create standardized output structure."""
    return {
        "success": success,
        "data": data,
        "error": error,
        "metadata": {
            "skill": SKILL_NAME,
            "version": VERSION,
            "inputs_hash": inputs_hash,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
    }


def compute_inputs_hash(data: Dict[str, Any]) -> str:
    """Compute a hash of inputs for reproducibility tracking."""
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:12]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate Levelized Cost of Energy (LCOE)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From stdin
  echo '{"capex_usd": 1000000, "annual_generation_mwh": 2000, "project_lifetime_years": 25, "discount_rate": 0.08}' | python calculate_lcoe.py

  # From file
  python calculate_lcoe.py --input project.json --output result.json
        """
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input JSON file path"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print JSON output"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} {VERSION}"
    )

    args = parser.parse_args()

    # Read input
    try:
        if args.input:
            with open(args.input, "r") as f:
                input_data = json.load(f)
        else:
            input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        output = create_output(
            success=False,
            error={
                "code": "INVALID_JSON",
                "message": f"Failed to parse input JSON: {str(e)}",
                "field": "input",
                "received": None,
                "expected": "Valid JSON object"
            }
        )
        print(json.dumps(output, indent=2 if args.pretty else None))
        sys.exit(1)
    except FileNotFoundError:
        output = create_output(
            success=False,
            error={
                "code": "FILE_NOT_FOUND",
                "message": f"Input file not found: {args.input}",
                "field": "input",
                "received": args.input,
                "expected": "Existing file path"
            }
        )
        print(json.dumps(output, indent=2 if args.pretty else None))
        sys.exit(1)

    # Compute hash for reproducibility
    inputs_hash = compute_inputs_hash(input_data)

    # Validate input
    validated = validate_input(input_data)

    # Check if validation returned an error
    if "code" in validated:
        output = create_output(
            success=False,
            error=validated,
            inputs_hash=inputs_hash
        )
        result_json = json.dumps(output, indent=2 if args.pretty else None)

        if args.output:
            with open(args.output, "w") as f:
                f.write(result_json)
        else:
            print(result_json)
        sys.exit(1)

    # Calculate LCOE
    result = calculate_lcoe(validated)

    # Create output
    output = create_output(
        success=True,
        data=result,
        inputs_hash=inputs_hash
    )

    result_json = json.dumps(output, indent=2 if args.pretty else None)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(result_json)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
