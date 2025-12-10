---
# Identification
name: lcoe-calculator
title: Levelized Cost of Energy (LCOE) Calculator
version: 1.0.0
description: Calculate the levelized cost of energy for power generation projects using industry-standard NREL/IEA methodology.

# Classification
category: financial-modeling
tags:
  - energy
  - finance
  - investment
  - renewable
  - solar
  - wind
  - economics

# Invocation Triggers
triggers:
  - "calculate LCOE"
  - "levelized cost of energy"
  - "compare project economics"
  - "energy cost analysis"
  - "project financial comparison"
  - "cost per MWh"
  - "cost per kWh"

# Agent Access Control
agents:
  - INVESTMENT_INTELLIGENCE
  - COST_PREDICTION
  - CFO
  - ANALYST

# Dependencies
dependencies:
  runtime: python3.9+
  packages: []  # No external packages - uses only Python standard library
  external_data: []  # No external data required

# Execution Limits
timeout_seconds: 30
max_input_size_kb: 100

# Audit Trail
author: GreenCIO Platform
created: 2025-12-08
updated: 2025-12-08
review_status: reference-implementation
---

# Levelized Cost of Energy (LCOE) Calculator

## Purpose

The LCOE Calculator computes the levelized cost of energy for power generation projects, enabling apples-to-apples comparison of different energy technologies regardless of their cost structures, lifetimes, or capacity factors.

LCOE represents the per-unit cost of electricity over a project's lifetime, accounting for:
- Initial capital expenditure (CAPEX)
- Ongoing operations and maintenance (O&M)
- Fuel costs (if applicable)
- The time value of money (discount rate)

## When to Use

Invoke this skill when the user:
- Asks to compare the economics of different energy projects
- Needs to calculate the cost per MWh or kWh for a generation asset
- Wants to evaluate the financial viability of a renewable energy investment
- Requires sensitivity analysis on project cost assumptions
- Needs standardized cost metrics for investment decisions

**Example queries that should trigger this skill:**
- "What's the LCOE for a 100MW solar farm with $80M capex?"
- "Compare the cost of wind vs solar for our portfolio"
- "How does the discount rate affect our project economics?"
- "Calculate the levelized cost assuming 25-year lifetime"

## When NOT to Use

Do not use this skill when:
- User needs real-time market prices (use market data feeds instead)
- Analysis requires tax credits/incentives modeling (extend with tax module)
- User needs full project finance model (NPV, IRR, payback)
- Comparing against retail electricity prices (different cost basis)

## Inputs

### Required Parameters

| Parameter | Type | Unit | Description |
|-----------|------|------|-------------|
| `capex_usd` | number | USD | Total capital expenditure |
| `annual_generation_mwh` | number | MWh | Expected annual energy generation |
| `project_lifetime_years` | integer | years | Project operational lifetime |
| `discount_rate` | number | decimal | Discount rate (e.g., 0.08 for 8%) |

### Optional Parameters

| Parameter | Type | Unit | Default | Description |
|-----------|------|------|---------|-------------|
| `annual_opex_usd` | number | USD | 0 | Annual O&M costs |
| `annual_fuel_cost_usd` | number | USD | 0 | Annual fuel costs |
| `opex_escalation_rate` | number | decimal | 0.02 | Annual O&M cost escalation |
| `fuel_escalation_rate` | number | decimal | 0.02 | Annual fuel cost escalation |
| `degradation_rate` | number | decimal | 0.005 | Annual generation degradation |
| `capacity_mw` | number | MW | null | Nameplate capacity (for reporting) |
| `technology` | string | - | "generic" | Technology type for labeling |

## Outputs

```json
{
  "success": true,
  "data": {
    "lcoe_usd_per_mwh": 45.23,
    "lcoe_usd_per_kwh": 0.04523,
    "total_lifecycle_cost_usd": 1523456.78,
    "total_lifetime_generation_mwh": 33687.45,
    "npv_costs_usd": 1234567.89,
    "npv_generation_mwh": 27298.12,
    "annual_breakdown": [
      {
        "year": 1,
        "generation_mwh": 2000,
        "opex_usd": 20000,
        "fuel_usd": 0,
        "total_cost_usd": 20000,
        "discounted_cost_usd": 18518.52,
        "discounted_generation_mwh": 1851.85
      }
    ],
    "sensitivity": {
      "discount_rate_impact": { ... },
      "capex_impact": { ... }
    }
  },
  "metadata": {
    "skill": "lcoe-calculator",
    "version": "1.0.0",
    "inputs_hash": "abc123",
    "calculated_at": "2025-12-08T10:30:00Z"
  }
}
```

## Scripts

### `calculate_lcoe.py` (Primary)
Main LCOE calculation with full annual breakdown.

```bash
# Via stdin/stdout
echo '{"capex_usd": 1000000, ...}' | python calculate_lcoe.py

# Via file arguments
python calculate_lcoe.py --input project.json --output result.json
```

### `sensitivity_analysis.py`
Run sensitivity analysis varying key parameters.

```bash
python sensitivity_analysis.py --input project.json --vary discount_rate --range 0.04,0.12,0.01
```

### `compare_projects.py`
Compare LCOE across multiple project configurations.

```bash
python compare_projects.py --inputs solar.json wind.json gas.json
```

## Examples

### Basic Solar Project

**Input:**
```json
{
  "technology": "solar_pv",
  "capacity_mw": 100,
  "capex_usd": 80000000,
  "annual_opex_usd": 800000,
  "annual_generation_mwh": 200000,
  "project_lifetime_years": 25,
  "discount_rate": 0.08,
  "degradation_rate": 0.005
}
```

**Output:**
```json
{
  "success": true,
  "data": {
    "lcoe_usd_per_mwh": 42.15,
    "lcoe_usd_per_kwh": 0.04215,
    "total_lifecycle_cost_usd": 98456789,
    "npv_generation_mwh": 2335678
  }
}
```

### Wind Project with Fuel (Hybrid)

**Input:**
```json
{
  "technology": "wind_gas_hybrid",
  "capacity_mw": 50,
  "capex_usd": 60000000,
  "annual_opex_usd": 1200000,
  "annual_fuel_cost_usd": 500000,
  "annual_generation_mwh": 150000,
  "project_lifetime_years": 20,
  "discount_rate": 0.10,
  "fuel_escalation_rate": 0.03
}
```

## Methodology

### LCOE Formula

The Levelized Cost of Energy is calculated as:

```
LCOE = NPV(Total Costs) / NPV(Total Generation)

     = [CAPEX + Σ(O&M_t + Fuel_t) / (1+r)^t] / [Σ(E_t) / (1+r)^t]
```

Where:
- **CAPEX**: Initial capital expenditure (year 0)
- **O&M_t**: Operations & maintenance cost in year t
- **Fuel_t**: Fuel cost in year t
- **E_t**: Energy generated in year t
- **r**: Discount rate (WACC)
- **t**: Year (1 to project lifetime)

### Cost Escalation

Annual costs escalate according to:
```
Cost_t = Cost_1 × (1 + escalation_rate)^(t-1)
```

### Generation Degradation

Annual generation degrades according to:
```
Generation_t = Generation_1 × (1 - degradation_rate)^(t-1)
```

### References

- NREL Annual Technology Baseline (ATB)
- IEA Projected Costs of Generating Electricity
- Lazard's Levelized Cost of Energy Analysis

## Validation Rules

| Parameter | Constraint | Error Code |
|-----------|------------|------------|
| `capex_usd` | > 0 | `INVALID_CAPEX` |
| `annual_generation_mwh` | > 0 | `INVALID_GENERATION` |
| `project_lifetime_years` | 1-50 | `INVALID_LIFETIME` |
| `discount_rate` | 0-0.30 | `INVALID_DISCOUNT_RATE` |
| `degradation_rate` | 0-0.10 | `INVALID_DEGRADATION` |
| `escalation_rate` | 0-0.20 | `INVALID_ESCALATION` |

## Integration Notes

### For Investment Intelligence Agent
Use LCOE to:
- Screen potential investments against target thresholds
- Compare acquisition targets on standardized basis
- Validate developer pro-forma assumptions

### For Cost Prediction Agent
Use LCOE to:
- Benchmark portfolio assets against market
- Identify underperforming assets
- Project future cost curves for technology types
