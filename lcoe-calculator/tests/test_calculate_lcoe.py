#!/usr/bin/env python3
"""
Tests for LCOE Calculator

Run with: python -m pytest tests/test_calculate_lcoe.py -v
Or: python test_calculate_lcoe.py
"""

import json
import subprocess
import sys
import os
from pathlib import Path

# Add scripts to path
SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from calculate_lcoe import validate_input, calculate_lcoe, LCOEInput


def run_script(input_data: dict, script_name: str = "calculate_lcoe.py") -> dict:
    """Execute script and return parsed output."""
    script_path = SCRIPTS_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )
    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"Script failed: {result.stderr}")
    return json.loads(result.stdout)


class TestValidation:
    """Test input validation."""

    def test_valid_minimal_input(self):
        """Test validation with only required fields."""
        data = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08
        }
        result = validate_input(data)
        assert "code" not in result
        assert result["capex_usd"] == 1000000

    def test_valid_full_input(self):
        """Test validation with all fields."""
        data = {
            "capex_usd": 80000000,
            "annual_generation_mwh": 200000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08,
            "annual_opex_usd": 800000,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0.02,
            "degradation_rate": 0.005,
            "capacity_mw": 100,
            "technology": "solar_pv"
        }
        result = validate_input(data)
        assert "code" not in result
        assert result["technology"] == "solar_pv"

    def test_missing_required_field(self):
        """Test validation fails for missing required field."""
        data = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25
            # missing discount_rate
        }
        result = validate_input(data)
        assert result["code"] == "MISSING_REQUIRED_FIELD"
        assert result["field"] == "discount_rate"

    def test_invalid_capex(self):
        """Test validation fails for negative capex."""
        data = {
            "capex_usd": -1000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08
        }
        result = validate_input(data)
        assert result["code"] == "INVALID_CAPEX"

    def test_invalid_discount_rate(self):
        """Test validation fails for out-of-range discount rate."""
        data = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.50  # 50% is too high
        }
        result = validate_input(data)
        assert result["code"] == "INVALID_DISCOUNT_RATE"

    def test_invalid_lifetime(self):
        """Test validation fails for invalid lifetime."""
        data = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 60,  # Max is 50
            "discount_rate": 0.08
        }
        result = validate_input(data)
        assert result["code"] == "INVALID_LIFETIME"


class TestLCOECalculation:
    """Test LCOE calculation logic."""

    def test_basic_calculation(self):
        """Test basic LCOE calculation."""
        inputs: LCOEInput = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08,
            "annual_opex_usd": 0,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0.02,
            "fuel_escalation_rate": 0.02,
            "degradation_rate": 0,
            "technology": "test"
        }
        result = calculate_lcoe(inputs)

        assert "lcoe_usd_per_mwh" in result
        assert result["lcoe_usd_per_mwh"] > 0
        # Allow for rounding differences (values are rounded in output)
        assert abs(result["lcoe_usd_per_kwh"] - result["lcoe_usd_per_mwh"] / 1000) < 0.0001

    def test_with_opex(self):
        """Test LCOE calculation with O&M costs."""
        inputs: LCOEInput = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08,
            "annual_opex_usd": 20000,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0.02,
            "fuel_escalation_rate": 0.02,
            "degradation_rate": 0,
            "technology": "test"
        }
        result = calculate_lcoe(inputs)

        # LCOE should be higher with O&M costs
        assert result["lcoe_usd_per_mwh"] > 0
        assert result["npv_costs_usd"] > 1000000  # More than just CAPEX

    def test_with_degradation(self):
        """Test LCOE calculation with generation degradation."""
        inputs_no_deg: LCOEInput = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08,
            "annual_opex_usd": 0,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0.02,
            "fuel_escalation_rate": 0.02,
            "degradation_rate": 0,
            "technology": "test"
        }
        inputs_with_deg: LCOEInput = {
            **inputs_no_deg,
            "degradation_rate": 0.01
        }

        result_no_deg = calculate_lcoe(inputs_no_deg)
        result_with_deg = calculate_lcoe(inputs_with_deg)

        # LCOE should be higher with degradation (less generation)
        assert result_with_deg["lcoe_usd_per_mwh"] > result_no_deg["lcoe_usd_per_mwh"]

    def test_annual_breakdown_length(self):
        """Test annual breakdown has correct number of years."""
        inputs: LCOEInput = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08,
            "annual_opex_usd": 20000,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0.02,
            "fuel_escalation_rate": 0.02,
            "degradation_rate": 0.005,
            "technology": "test"
        }
        result = calculate_lcoe(inputs)

        assert len(result["annual_breakdown"]) == 25
        assert result["annual_breakdown"][0]["year"] == 1
        assert result["annual_breakdown"][-1]["year"] == 25

    def test_capacity_factor_calculation(self):
        """Test capacity factor is calculated when capacity provided."""
        inputs: LCOEInput = {
            "capex_usd": 80000000,
            "annual_generation_mwh": 200000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08,
            "annual_opex_usd": 800000,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0.02,
            "fuel_escalation_rate": 0.02,
            "degradation_rate": 0.005,
            "capacity_mw": 100,
            "technology": "solar_pv"
        }
        result = calculate_lcoe(inputs)

        # 100 MW * 8760 hours = 876,000 MWh max
        # 200,000 / 876,000 = ~22.8%
        assert result["capacity_factor"] is not None
        assert 20 < result["capacity_factor"] < 25


class TestScriptExecution:
    """Test script execution via subprocess."""

    def test_script_success(self):
        """Test script executes successfully."""
        input_data = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08
        }
        result = run_script(input_data)

        assert result["success"] is True
        assert "lcoe_usd_per_mwh" in result["data"]
        assert result["metadata"]["skill"] == "lcoe-calculator"

    def test_script_validation_error(self):
        """Test script returns error for invalid input."""
        input_data = {
            "capex_usd": -1000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08
        }
        result = run_script(input_data)

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_CAPEX"

    def test_example_solar_project(self):
        """Test with example solar project."""
        example_path = SKILL_DIR / "examples" / "solar_100mw.json"
        if example_path.exists():
            with open(example_path) as f:
                input_data = json.load(f)

            result = run_script(input_data)
            assert result["success"] is True
            # Solar LCOE should be reasonable (20-80 $/MWh typically)
            assert 20 < result["data"]["lcoe_usd_per_mwh"] < 100


class TestKnownValues:
    """Test against known/expected values."""

    def test_simple_lcoe(self):
        """
        Test simple case where we can calculate expected LCOE manually.

        CAPEX: $1,000,000
        Generation: 2,000 MWh/year
        Lifetime: 10 years
        Discount rate: 0% (no discounting for easy math)
        No O&M, no degradation

        Expected LCOE = $1,000,000 / (2,000 * 10) = $50/MWh
        """
        inputs: LCOEInput = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 10,
            "discount_rate": 0.0,
            "annual_opex_usd": 0,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0,
            "fuel_escalation_rate": 0,
            "degradation_rate": 0,
            "technology": "test"
        }
        result = calculate_lcoe(inputs)

        # With 0% discount rate, NPV = simple sum
        assert result["lcoe_usd_per_mwh"] == 50.0

    def test_discount_effect(self):
        """
        Test that discounting increases LCOE.

        Higher discount rate means future generation is worth less,
        so LCOE should be higher.
        """
        base_inputs: LCOEInput = {
            "capex_usd": 1000000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.05,
            "annual_opex_usd": 0,
            "annual_fuel_cost_usd": 0,
            "opex_escalation_rate": 0,
            "fuel_escalation_rate": 0,
            "degradation_rate": 0,
            "technology": "test"
        }

        high_discount: LCOEInput = {**base_inputs, "discount_rate": 0.15}

        result_low = calculate_lcoe(base_inputs)
        result_high = calculate_lcoe(high_discount)

        # Higher discount = higher LCOE
        assert result_high["lcoe_usd_per_mwh"] > result_low["lcoe_usd_per_mwh"]


def run_tests():
    """Run all tests without pytest."""
    import traceback

    test_classes = [
        TestValidation,
        TestLCOECalculation,
        TestScriptExecution,
        TestKnownValues
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"✓ {test_class.__name__}.{method_name}")
                    passed += 1
                except Exception as e:
                    print(f"✗ {test_class.__name__}.{method_name}")
                    print(f"  Error: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
