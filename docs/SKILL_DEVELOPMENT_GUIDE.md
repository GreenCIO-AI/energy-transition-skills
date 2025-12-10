# GreenCIO Skill Development Guide

> **Version**: 1.0.0
> **Created**: 2025-12-08
> **Status**: Reference Implementation

This document formalizes the "Skills-First" approach for building domain expertise into GreenCIO's multi-agent system. Skills are portable, versioned packages of procedural knowledge that agents can invoke to perform specialized tasks.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Skill Architecture](#skill-architecture)
3. [Directory Structure](#directory-structure)
4. [The skill.md Specification](#the-skillmd-specification)
5. [Script Development Guidelines](#script-development-guidelines)
6. [Agent Integration](#agent-integration)
7. [Testing & Validation](#testing--validation)
8. [Reference Implementation: LCOE Calculator](#reference-implementation-lcoe-calculator)

---

## Philosophy

### Core Principles

1. **Skills over Bespoke Agents**: Don't create a unique agent for every task. Build reusable Skills that any agent can invoke.

2. **Code as Interface**: Skills contain executable scripts that agents can run. This provides:
   - Self-documenting behavior
   - Reproducible results
   - Version-controlled logic
   - Agent-modifiable procedures

3. **Domain Expertise Packaging**: A general AI model needs procedural knowledge to act as an expert. Skills package "how to do things" so agents don't guess.

4. **Progressive Disclosure**: Only load full skill instructions when the agent decides to use that skill. This preserves context window budget.

### When to Create a Skill

Create a skill when:
- A task requires domain-specific calculations or procedures
- The same logic is needed across multiple agents
- Accuracy depends on specific formulas or algorithms
- Results need to be reproducible and auditable
- Non-technical team members should be able to review/modify the logic

---

## Skill Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Runtime                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌───────────────┐    ┌───────────────┐                   │
│   │ Investment    │    │ Cost          │                   │
│   │ Intelligence  │    │ Prediction    │                   │
│   │ Agent         │    │ Agent         │                   │
│   └───────┬───────┘    └───────┬───────┘                   │
│           │                    │                            │
│           └────────┬───────────┘                            │
│                    │                                        │
│           ┌────────▼────────┐                              │
│           │  Skill Loader   │                              │
│           │  (TypeScript)   │                              │
│           └────────┬────────┘                              │
│                    │                                        │
└────────────────────┼────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Skills Library                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  skills/                                                    │
│  ├── lcoe-calculator/      ← Reference Implementation       │
│  │   ├── skill.md          ← Entry point & metadata         │
│  │   ├── scripts/          ← Executable Python/Bash         │
│  │   ├── schemas/          ← Input/Output JSON schemas      │
│  │   └── examples/         ← Sample inputs & outputs        │
│  │                                                          │
│  ├── ppa-analyzer/                                          │
│  ├── carbon-calculator/                                     │
│  └── ...                                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

Every skill follows this standard structure:

```
skills/
└── {skill-name}/
    ├── skill.md              # Required: Entry point with metadata
    ├── scripts/              # Required: Executable code
    │   ├── main.py           # Primary calculation/logic
    │   ├── validate.py       # Input validation
    │   └── requirements.txt  # Python dependencies (if any)
    ├── schemas/              # Recommended: JSON schemas
    │   ├── input.schema.json
    │   └── output.schema.json
    ├── examples/             # Recommended: Sample data
    │   ├── input.json
    │   └── output.json
    └── tests/                # Recommended: Test cases
        └── test_main.py
```

### Naming Conventions

- **Skill folder**: lowercase with hyphens (`lcoe-calculator`, `ppa-analyzer`)
- **Scripts**: lowercase with underscores (`calculate_lcoe.py`)
- **Schemas**: `{type}.schema.json`
- **Examples**: descriptive names (`solar_project_input.json`)

---

## The skill.md Specification

The `skill.md` file is the entry point for every skill. It uses YAML frontmatter for machine-readable metadata and markdown for human-readable instructions.

### Required Frontmatter Fields

```yaml
---
# Identification
name: lcoe-calculator                    # Unique skill identifier
title: LCOE Calculator                   # Human-readable name
version: 1.0.0                           # Semantic version

# Classification
category: financial-modeling             # Domain category
tags: [energy, finance, investment]      # Searchable tags

# Invocation
triggers:                                # Phrases that should invoke this skill
  - "calculate LCOE"
  - "levelized cost of energy"
  - "compare project economics"

# Agent Access
agents:                                  # Agents authorized to use this skill
  - INVESTMENT_INTELLIGENCE
  - COST_PREDICTION
  - CFO

# Dependencies
dependencies:                            # External requirements
  runtime: python3.9+
  packages: []                           # Empty = no external packages needed
  external_data: []                      # Empty = no external data needed
---
```

### Optional Frontmatter Fields

```yaml
---
# Execution
timeout_seconds: 30                      # Max execution time
max_input_size_kb: 100                   # Input size limit

# Audit
author: GreenCIO Team
created: 2025-12-08
updated: 2025-12-08
review_status: approved
---
```

### Markdown Body Structure

```markdown
# {Skill Title}

## Purpose
Brief description of what this skill does and why it exists.

## When to Use
Specific scenarios where this skill should be invoked.

## When NOT to Use
Cases where this skill is inappropriate (prevents misuse).

## Inputs
Description of required and optional inputs with types.

## Outputs
Description of what the skill returns.

## Scripts
List of available scripts with descriptions.

## Examples
Sample usage scenarios.

## Methodology
Technical details, formulas, references for auditability.
```

---

## Script Development Guidelines

### Python Script Template

```python
#!/usr/bin/env python3
"""
{Script Name}
{Brief description}

Usage:
    python {script_name}.py < input.json > output.json
    python {script_name}.py --input input.json --output output.json
"""

import json
import sys
import argparse
from typing import TypedDict

# Type definitions for inputs
class Input(TypedDict):
    # Define input structure
    pass

# Type definitions for outputs
class Output(TypedDict):
    # Define output structure
    pass

def validate_input(data: dict) -> Input:
    """Validate and parse input data."""
    # Validation logic
    return data

def calculate(input_data: Input) -> Output:
    """Core calculation logic."""
    # Implementation
    pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', '-i', type=str, help='Input JSON file')
    parser.add_argument('--output', '-o', type=str, help='Output JSON file')
    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input) as f:
            input_data = json.load(f)
    else:
        input_data = json.load(sys.stdin)

    # Validate and calculate
    validated = validate_input(input_data)
    result = calculate(validated)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
```

### Script Requirements

1. **No External Dependencies When Possible**: Prefer Python standard library
2. **JSON In/Out**: Accept JSON input, produce JSON output
3. **Stdin/Stdout Support**: Work with pipes for agent integration
4. **Error Handling**: Return structured error messages
5. **Deterministic**: Same input = same output (no randomness without seed)

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Discount rate must be between 0 and 1",
    "field": "discount_rate",
    "received": 1.5
  }
}
```

---

## Agent Integration

### TypeScript Skill Loader

The skill loader provides a clean interface for agents to discover and execute skills:

```typescript
// lib/skills/loader.ts

interface SkillMetadata {
  name: string;
  title: string;
  version: string;
  category: string;
  triggers: string[];
  agents: string[];
  dependencies: {
    runtime: string;
    packages: string[];
    external_data: string[];
  };
}

interface SkillExecutionResult {
  success: boolean;
  data?: unknown;
  error?: {
    code: string;
    message: string;
  };
  metadata: {
    skill: string;
    version: string;
    executionTimeMs: number;
  };
}

class SkillLoader {
  // Load skill metadata (progressive disclosure - metadata only)
  async getSkillMetadata(skillName: string): Promise<SkillMetadata>;

  // Load full skill instructions (when agent decides to use it)
  async getSkillInstructions(skillName: string): Promise<string>;

  // Execute a skill script
  async executeSkill(
    skillName: string,
    scriptName: string,
    input: unknown
  ): Promise<SkillExecutionResult>;

  // Find skills matching a query
  async findSkills(query: string, agentRole: string): Promise<SkillMetadata[]>;
}
```

### Agent Usage Pattern

```typescript
// In specialist agent execute() method

async execute(context: AgentContext, query: AgentQuery): Promise<AgentResponse> {
  // 1. Check if query matches a skill trigger
  const matchingSkills = await this.skillLoader.findSkills(
    query.query,
    this.role
  );

  if (matchingSkills.length > 0) {
    // 2. Load full instructions for matched skill
    const skill = matchingSkills[0];
    const instructions = await this.skillLoader.getSkillInstructions(skill.name);

    // 3. Extract parameters from query using LLM
    const params = await this.extractParameters(query.query, instructions);

    // 4. Execute skill
    const result = await this.skillLoader.executeSkill(
      skill.name,
      'main.py',
      params
    );

    // 5. Format response
    return this.formatSkillResponse(result, skill);
  }

  // Fall back to standard agent processing
  return super.execute(context, query);
}
```

---

## Testing & Validation

### Test Categories

1. **Unit Tests**: Test individual calculation functions
2. **Integration Tests**: Test full script execution with sample inputs
3. **Trigger Tests**: Verify skills are invoked for correct queries
4. **Output Validation**: Verify outputs match expected schemas

### Test File Template

```python
# tests/test_main.py
import json
import subprocess
import pytest
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPT = SKILL_DIR / "scripts" / "main.py"

def run_skill(input_data: dict) -> dict:
    """Execute skill and return output."""
    result = subprocess.run(
        ["python3", str(SCRIPT)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)

class TestLCOECalculator:
    def test_basic_calculation(self):
        input_data = {
            "capex_usd": 1000000,
            "annual_opex_usd": 20000,
            "annual_generation_mwh": 2000,
            "project_lifetime_years": 25,
            "discount_rate": 0.08
        }
        result = run_skill(input_data)
        assert result["success"] is True
        assert "lcoe_usd_per_mwh" in result["data"]

    def test_validation_error(self):
        input_data = {"capex_usd": -1000}  # Invalid
        result = run_skill(input_data)
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
```

---

## Reference Implementation: LCOE Calculator

The `lcoe-calculator` skill serves as the reference implementation demonstrating all concepts in this guide.

### Why LCOE Calculator?

- **Zero External Dependencies**: Pure mathematical calculations
- **Well-Defined Formula**: Industry-standard NREL/IEA methodology
- **High Value**: Used by Investment Intelligence and Cost Prediction agents
- **Auditable**: Clear formula that stakeholders can verify

### Implementation Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| Entry Point | `skills/lcoe-calculator/skill.md` | Metadata and instructions |
| Main Script | `scripts/calculate_lcoe.py` | Core LCOE calculation |
| Sensitivity | `scripts/sensitivity_analysis.py` | Parameter sensitivity |
| Input Schema | `schemas/input.schema.json` | Input validation |
| Output Schema | `schemas/output.schema.json` | Output structure |
| Examples | `examples/*.json` | Sample inputs/outputs |
| Tests | `tests/test_calculate_lcoe.py` | Validation tests |

### LCOE Formula

```
LCOE = Total Lifecycle Cost (NPV) / Total Lifetime Energy (NPV)

     = [CAPEX + Σ(O&M_t + Fuel_t) / (1+r)^t] / [Σ(E_t) / (1+r)^t]

Where:
  CAPEX = Initial capital expenditure ($)
  O&M_t = Operations & maintenance cost in year t ($)
  Fuel_t = Fuel cost in year t ($ - zero for renewables)
  E_t = Energy generated in year t (MWh)
  r = Discount rate (decimal)
  t = Year (1 to project lifetime)
```

---

## Checklist for New Skills

- [ ] Create skill folder with correct naming
- [ ] Write `skill.md` with complete frontmatter
- [ ] Implement main script following template
- [ ] Create input/output JSON schemas
- [ ] Add example inputs and expected outputs
- [ ] Write unit and integration tests
- [ ] Test script works via stdin/stdout
- [ ] Verify no external dependencies (or document them)
- [ ] Register skill in skill loader
- [ ] Update agent capabilities if needed

---

## Appendix: Skill Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `financial-modeling` | Investment analysis, valuations | LCOE, NPV, IRR |
| `emissions-calculation` | Carbon and GHG calculations | Scope 1/2/3, footprint |
| `contract-analysis` | Legal document parsing | PPA analyzer, REC tracker |
| `grid-operations` | Power grid calculations | Load forecast, curtailment |
| `regulatory-compliance` | Compliance checking | CBAM, SEC disclosure |
| `asset-management` | Physical asset optimization | Maintenance, lifecycle |
| `reporting` | Report generation | ESG reports, dashboards |

---

*This document is version-controlled and should be updated as the skill system evolves.*
