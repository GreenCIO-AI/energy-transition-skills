# Energy Transition Skills

Open source AI skills library for the energy transition. These Skills are portable, versioned packages of procedural knowledge that AI agents can invoke to perform specialized domain tasks.

## Philosophy

> "Stop building bespoke agents for every task. Build reusable Skills that any agent can invoke. Code is the universal interface."

The energy transition requires collective intelligence across finance, engineering, policy, and sustainability. Skills let domain experts contribute procedural knowledge without needing to understand the full AI system.

## Available Skills

| Skill | Category | Description | Status |
|-------|----------|-------------|--------|
| [lcoe-calculator](./lcoe-calculator/) | Financial Modeling | Levelized Cost of Energy calculation using NREL/IEA methodology | Reference Implementation |

## Skill Structure

Every skill follows this standard structure:

```
skill-name/
├── skill.md              # Entry point with YAML metadata
├── scripts/              # Executable Python scripts
│   ├── main.py           # Primary calculation
│   └── requirements.txt  # Dependencies (prefer none)
├── schemas/              # JSON schemas for validation
│   ├── input.schema.json
│   └── output.schema.json
├── examples/             # Sample inputs/outputs
└── tests/                # Test cases
```

## How to Contribute

### 1. Choose a Skill Gap

Skills needed for the energy transition:

**Financial Modeling**
- `project-npv-irr` - NPV/IRR/Payback modeling
- `carbon-price-modeler` - Carbon price scenarios
- `green-bond-analyzer` - Green bond verification

**Emissions & Carbon**
- `carbon-footprint` - Scope 1/2/3 calculator
- `emissions-reporter` - CDP/GRI/SASB formatter
- `offset-validator` - Carbon offset quality scoring

**Grid & Energy**
- `load-forecaster` - Demand time-series forecasting
- `curtailment-optimizer` - Peak load optimization
- `solar-yield` - PV generation calculator
- `wind-yield` - Wind generation calculator

**Contracts & Compliance**
- `ppa-analyzer` - Power Purchase Agreement parser
- `rec-tracker` - Renewable certificate management
- `cbam-compliance` - EU CBAM checker
- `sec-climate-disclosure` - SEC climate risk formatter

**Asset Management**
- `predictive-maintenance` - ML-based maintenance scheduling
- `battery-lifecycle` - Storage degradation modeling
- `equipment-lifecycle` - Replacement timing optimizer

### 2. Follow the Template

Use the [lcoe-calculator](./lcoe-calculator/) as your reference implementation. Copy the folder structure and adapt it.

### 3. Write Python Scripts

- Use only Python standard library when possible
- Accept JSON input via stdin
- Output JSON to stdout
- Include validation and error handling

### 4. Add Tests & Examples

Include test cases and example inputs so others can validate and learn from your work.

### 5. Submit a Pull Request

Open a PR to this repository. Our agents will review and integrate your skill.

## Using Skills

### Via Command Line

```bash
# Calculate LCOE
echo '{"capex_usd": 1000000, "annual_generation_mwh": 2000, "project_lifetime_years": 25, "discount_rate": 0.08}' | python lcoe-calculator/scripts/calculate_lcoe.py

# Run sensitivity analysis
python lcoe-calculator/scripts/sensitivity_analysis.py --input lcoe-calculator/examples/solar_100mw.json --all

# Compare projects
python lcoe-calculator/scripts/compare_projects.py --inputs-dir lcoe-calculator/examples/
```

### Via TypeScript (Agent Integration)

```typescript
import { getSkillLoader } from '@/lib/skills';

const loader = getSkillLoader();

// Find matching skills
const matches = await loader.findSkills("calculate LCOE", "INVESTMENT_INTELLIGENCE");

// Execute a skill
const result = await loader.executeSkill('lcoe-calculator', 'calculate_lcoe.py', {
  capex_usd: 80000000,
  annual_generation_mwh: 200000,
  project_lifetime_years: 25,
  discount_rate: 0.08
});
```

## Documentation

- [Skill Development Guide](./docs/SKILL_DEVELOPMENT_GUIDE.md) - Comprehensive guide to creating skills

## Why Open Source Skills?

### Collective Intelligence
The energy transition requires expertise across finance, engineering, policy, and sustainability. Skills let domain experts contribute without needing to understand the full AI system.

### Non-Proprietary Knowledge
Skills encode public methodologies: NREL's LCOE formula, EPA emission factors, GHG Protocol calculations. This is procedural knowledge, not trade secrets.

### AI-Scale Execution
Your expertise gets executed by AI agents 24/7 across thousands of investment decisions. One contribution creates impact at scale.

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Contact

- Website: [greencio.com](https://www.greencio.com)
- Contribute: [greencio.com/contribute-skills](https://www.greencio.com/contribute-skills)
- X: [@greencio](https://x.com/greencio)
