# Integration Guide: Using Energy Transition Skills

This guide explains how to integrate and use Energy Transition Skills in your AI applications, whether you're building with the **Claude Agent SDK** or using **Claude Code** directly.

---

## Table of Contents

1. [Overview](#overview)
2. [Using Skills with Claude Code](#using-skills-with-claude-code)
3. [Using Skills with Claude Agent SDK](#using-skills-with-claude-agent-sdk)
4. [Skill Execution Patterns](#skill-execution-patterns)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

---

## Overview

Energy Transition Skills are portable, executable modules that encode domain expertise as Python scripts. Each skill:

- Accepts **JSON input** via stdin or file argument
- Produces **JSON output** to stdout
- Requires **no external dependencies** (Python standard library only)
- Is **deterministic** (same input → same output)

This design makes skills easily invokable from any environment—whether that's Claude Code running in a terminal, or a Claude Agent SDK application running in the cloud.

---

## Using Skills with Claude Code

Claude Code can execute skills directly using the Bash tool. Here are the patterns for using skills effectively.

### Quick Start

```bash
# Clone the skills repository
git clone https://github.com/GreenCIO-AI/energy-transition-skills.git
cd energy-transition-skills

# Run LCOE calculation with inline JSON
echo '{"capex_usd": 80000000, "annual_generation_mwh": 200000, "project_lifetime_years": 25, "discount_rate": 0.08}' | python lcoe-calculator/scripts/calculate_lcoe.py
```

### Pattern 1: Inline JSON Input

Best for quick calculations with a few parameters:

```bash
echo '{
  "technology": "solar_pv",
  "capacity_mw": 100,
  "capex_usd": 80000000,
  "annual_opex_usd": 800000,
  "annual_generation_mwh": 200000,
  "project_lifetime_years": 25,
  "discount_rate": 0.08,
  "degradation_rate": 0.005
}' | python lcoe-calculator/scripts/calculate_lcoe.py
```

### Pattern 2: File-Based Input

Best for complex inputs or when reusing configurations:

```bash
# Use an example file
python lcoe-calculator/scripts/calculate_lcoe.py --input lcoe-calculator/examples/solar_100mw.json

# Save output to file
python lcoe-calculator/scripts/calculate_lcoe.py --input lcoe-calculator/examples/solar_100mw.json --output result.json
```

### Pattern 3: Comparing Multiple Projects

```bash
# Compare all example projects
python lcoe-calculator/scripts/compare_projects.py --inputs-dir lcoe-calculator/examples/

# Compare specific projects
python lcoe-calculator/scripts/compare_projects.py --inputs lcoe-calculator/examples/solar_100mw.json lcoe-calculator/examples/wind_onshore_50mw.json
```

### Pattern 4: Sensitivity Analysis

```bash
# Run full sensitivity analysis
python lcoe-calculator/scripts/sensitivity_analysis.py --input lcoe-calculator/examples/solar_100mw.json --all

# Analyze specific parameter
python lcoe-calculator/scripts/sensitivity_analysis.py --input lcoe-calculator/examples/solar_100mw.json --vary discount_rate --range 0.04,0.12,0.01
```

### Claude Code Workflow Example

When a user asks Claude Code to analyze energy project economics:

```
User: "Compare the LCOE of a 100MW solar farm vs a 50MW wind farm"

Claude Code:
1. Reads the skill documentation (skill.md) to understand inputs
2. Creates JSON input files for each project
3. Executes: python lcoe-calculator/scripts/compare_projects.py --inputs solar.json wind.json
4. Parses the JSON output and presents results to user
```

---

## Using Skills with Claude Agent SDK

The Claude Agent SDK enables building autonomous agents that can invoke skills as tools. Here's how to integrate skills into your SDK-based application.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────────┐    ┌─────────────────┐           │
│   │  Claude Agent   │    │  Skill Loader   │           │
│   │  (SDK Client)   │───▶│  (TypeScript)   │           │
│   └─────────────────┘    └────────┬────────┘           │
│                                   │                     │
│                          ┌────────▼────────┐           │
│                          │  Skills Library  │           │
│                          │  (Python Scripts)│           │
│                          └─────────────────┘           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Step 1: Set Up the Skill Loader

Create a TypeScript module to load and execute skills:

```typescript
// lib/skills/loader.ts
import { spawn } from 'child_process';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'yaml';

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

export class SkillLoader {
  private skillsDir: string;
  private skillsCache: Map<string, SkillMetadata> = new Map();

  constructor(skillsDir: string = './skills') {
    this.skillsDir = skillsDir;
  }

  /**
   * Load skill metadata from skill.md frontmatter
   */
  async getSkillMetadata(skillName: string): Promise<SkillMetadata> {
    if (this.skillsCache.has(skillName)) {
      return this.skillsCache.get(skillName)!;
    }

    const skillPath = path.join(this.skillsDir, skillName, 'skill.md');
    const content = await fs.readFile(skillPath, 'utf-8');

    // Extract YAML frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!frontmatterMatch) {
      throw new Error(`No frontmatter found in ${skillPath}`);
    }

    const metadata = yaml.parse(frontmatterMatch[1]) as SkillMetadata;
    this.skillsCache.set(skillName, metadata);
    return metadata;
  }

  /**
   * Load full skill instructions (markdown body)
   */
  async getSkillInstructions(skillName: string): Promise<string> {
    const skillPath = path.join(this.skillsDir, skillName, 'skill.md');
    const content = await fs.readFile(skillPath, 'utf-8');

    // Remove frontmatter, return body
    return content.replace(/^---\n[\s\S]*?\n---\n/, '');
  }

  /**
   * Execute a skill script with JSON input
   */
  async executeSkill(
    skillName: string,
    scriptName: string,
    input: unknown
  ): Promise<SkillExecutionResult> {
    const startTime = Date.now();
    const scriptPath = path.join(this.skillsDir, skillName, 'scripts', scriptName);
    const metadata = await this.getSkillMetadata(skillName);

    return new Promise((resolve) => {
      const process = spawn('python3', [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let stdout = '';
      let stderr = '';

      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      // Send input as JSON
      process.stdin.write(JSON.stringify(input));
      process.stdin.end();

      process.on('close', (code) => {
        const executionTimeMs = Date.now() - startTime;

        if (code === 0) {
          try {
            const result = JSON.parse(stdout);
            resolve({
              ...result,
              metadata: {
                skill: skillName,
                version: metadata.version,
                executionTimeMs,
              },
            });
          } catch {
            resolve({
              success: false,
              error: {
                code: 'PARSE_ERROR',
                message: `Failed to parse skill output: ${stdout}`,
              },
              metadata: {
                skill: skillName,
                version: metadata.version,
                executionTimeMs,
              },
            });
          }
        } else {
          resolve({
            success: false,
            error: {
              code: 'EXECUTION_ERROR',
              message: stderr || `Script exited with code ${code}`,
            },
            metadata: {
              skill: skillName,
              version: metadata.version,
              executionTimeMs,
            },
          });
        }
      });
    });
  }

  /**
   * Find skills matching a query and agent role
   */
  async findSkills(query: string, agentRole: string): Promise<SkillMetadata[]> {
    const skillDirs = await fs.readdir(this.skillsDir);
    const matches: SkillMetadata[] = [];
    const queryLower = query.toLowerCase();

    for (const dir of skillDirs) {
      try {
        const metadata = await this.getSkillMetadata(dir);

        // Check if agent has access
        if (!metadata.agents.includes(agentRole) && !metadata.agents.includes('*')) {
          continue;
        }

        // Check if query matches any trigger
        const matchesTrigger = metadata.triggers.some(
          (trigger) => queryLower.includes(trigger.toLowerCase())
        );

        if (matchesTrigger) {
          matches.push(metadata);
        }
      } catch {
        // Skip invalid skill directories
      }
    }

    return matches;
  }
}

// Singleton instance
let loaderInstance: SkillLoader | null = null;

export function getSkillLoader(skillsDir?: string): SkillLoader {
  if (!loaderInstance) {
    loaderInstance = new SkillLoader(skillsDir);
  }
  return loaderInstance;
}
```

### Step 2: Define Skills as Agent Tools

Register skills as tools that Claude can invoke:

```typescript
// lib/agent/tools.ts
import { Tool } from '@anthropic-ai/sdk';
import { getSkillLoader } from '../skills/loader';

export const lcoeCalculatorTool: Tool = {
  name: 'calculate_lcoe',
  description: `Calculate the Levelized Cost of Energy (LCOE) for a power generation project.
Use this tool when the user wants to:
- Compare economics of different energy projects
- Calculate cost per MWh or kWh for generation assets
- Evaluate financial viability of renewable energy investments
- Run sensitivity analysis on project assumptions`,
  input_schema: {
    type: 'object',
    properties: {
      technology: {
        type: 'string',
        description: 'Technology type (e.g., solar_pv, wind_onshore, gas_ccgt)',
      },
      capacity_mw: {
        type: 'number',
        description: 'Nameplate capacity in MW',
      },
      capex_usd: {
        type: 'number',
        description: 'Total capital expenditure in USD',
      },
      annual_opex_usd: {
        type: 'number',
        description: 'Annual O&M costs in USD',
      },
      annual_generation_mwh: {
        type: 'number',
        description: 'Expected annual energy generation in MWh',
      },
      project_lifetime_years: {
        type: 'integer',
        description: 'Project operational lifetime (1-50 years)',
      },
      discount_rate: {
        type: 'number',
        description: 'Discount rate as decimal (e.g., 0.08 for 8%)',
      },
      degradation_rate: {
        type: 'number',
        description: 'Annual generation degradation rate (default: 0.005)',
      },
    },
    required: ['capex_usd', 'annual_generation_mwh', 'project_lifetime_years', 'discount_rate'],
  },
};

export async function handleToolCall(
  toolName: string,
  toolInput: Record<string, unknown>
): Promise<string> {
  const loader = getSkillLoader();

  switch (toolName) {
    case 'calculate_lcoe': {
      const result = await loader.executeSkill(
        'lcoe-calculator',
        'calculate_lcoe.py',
        toolInput
      );
      return JSON.stringify(result, null, 2);
    }
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}
```

### Step 3: Integrate with Claude Agent SDK

```typescript
// lib/agent/energy-agent.ts
import Anthropic from '@anthropic-ai/sdk';
import { lcoeCalculatorTool, handleToolCall } from './tools';

const client = new Anthropic();

export async function runEnergyAgent(userQuery: string): Promise<string> {
  const messages: Anthropic.MessageParam[] = [
    { role: 'user', content: userQuery },
  ];

  // Initial request with tools
  let response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4096,
    tools: [lcoeCalculatorTool],
    messages,
  });

  // Agentic loop: handle tool calls until done
  while (response.stop_reason === 'tool_use') {
    const toolUseBlock = response.content.find(
      (block) => block.type === 'tool_use'
    );

    if (!toolUseBlock || toolUseBlock.type !== 'tool_use') {
      break;
    }

    // Execute the skill
    const toolResult = await handleToolCall(
      toolUseBlock.name,
      toolUseBlock.input as Record<string, unknown>
    );

    // Continue conversation with tool result
    messages.push({ role: 'assistant', content: response.content });
    messages.push({
      role: 'user',
      content: [
        {
          type: 'tool_result',
          tool_use_id: toolUseBlock.id,
          content: toolResult,
        },
      ],
    });

    response = await client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      tools: [lcoeCalculatorTool],
      messages,
    });
  }

  // Extract final text response
  const textBlock = response.content.find((block) => block.type === 'text');
  return textBlock?.type === 'text' ? textBlock.text : '';
}
```

### Step 4: Usage Example

```typescript
// examples/analyze-project.ts
import { runEnergyAgent } from '../lib/agent/energy-agent';

async function main() {
  const query = `
    I'm evaluating a 100MW solar farm investment with the following parameters:
    - Total CAPEX: $80 million
    - Annual O&M: $800,000
    - Expected generation: 200,000 MWh/year
    - Project lifetime: 25 years
    - Our WACC is 8%
    - Assume 0.5% annual degradation

    What's the LCOE and how does it compare to current market prices?
  `;

  const response = await runEnergyAgent(query);
  console.log(response);
}

main();
```

---

## Skill Execution Patterns

### Pattern 1: Direct Execution

For simple, synchronous skill invocation:

```typescript
const result = await skillLoader.executeSkill(
  'lcoe-calculator',
  'calculate_lcoe.py',
  { capex_usd: 80000000, annual_generation_mwh: 200000, ... }
);
```

### Pattern 2: Progressive Disclosure

Load skill metadata first, then full instructions only when needed:

```typescript
// Stage 1: Quick metadata check
const metadata = await skillLoader.getSkillMetadata('lcoe-calculator');
console.log(`Found skill: ${metadata.title} v${metadata.version}`);

// Stage 2: Load full instructions when agent decides to use skill
const instructions = await skillLoader.getSkillInstructions('lcoe-calculator');
// Include instructions in agent prompt for parameter extraction
```

### Pattern 3: Multi-Skill Orchestration

Chain multiple skills for complex analyses:

```typescript
// Calculate LCOE for multiple projects
const projects = ['solar_100mw', 'wind_50mw', 'battery_25mw'];
const results = await Promise.all(
  projects.map(async (project) => {
    const input = await loadProjectConfig(project);
    return skillLoader.executeSkill('lcoe-calculator', 'calculate_lcoe.py', input);
  })
);

// Run comparison
const comparison = await skillLoader.executeSkill(
  'lcoe-calculator',
  'compare_projects.py',
  { projects: results.map(r => r.data) }
);
```

---

## Error Handling

Skills return structured errors that your application should handle:

```typescript
const result = await skillLoader.executeSkill('lcoe-calculator', 'calculate_lcoe.py', input);

if (!result.success) {
  switch (result.error?.code) {
    case 'VALIDATION_ERROR':
      // Invalid input parameters
      console.error(`Invalid input: ${result.error.message}`);
      break;
    case 'EXECUTION_ERROR':
      // Script failed to run
      console.error(`Execution failed: ${result.error.message}`);
      break;
    case 'PARSE_ERROR':
      // Output parsing failed
      console.error(`Parse error: ${result.error.message}`);
      break;
    default:
      console.error(`Unknown error: ${result.error?.message}`);
  }
}
```

### Common Validation Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| `INVALID_CAPEX` | capex_usd ≤ 0 | Provide positive CAPEX value |
| `INVALID_GENERATION` | annual_generation_mwh ≤ 0 | Provide positive generation |
| `INVALID_LIFETIME` | Outside 1-50 range | Use realistic project lifetime |
| `INVALID_DISCOUNT_RATE` | Outside 0-0.30 range | Use reasonable discount rate |

---

## Best Practices

### 1. Validate Inputs Before Execution

```typescript
function validateLCOEInput(input: unknown): asserts input is LCOEInput {
  if (typeof input !== 'object' || input === null) {
    throw new Error('Input must be an object');
  }

  const { capex_usd, annual_generation_mwh, project_lifetime_years, discount_rate } = input as Record<string, unknown>;

  if (typeof capex_usd !== 'number' || capex_usd <= 0) {
    throw new Error('capex_usd must be a positive number');
  }
  // ... additional validation
}
```

### 2. Cache Skill Metadata

```typescript
// Metadata rarely changes, cache it
const metadataCache = new Map<string, SkillMetadata>();

async function getCachedMetadata(skillName: string): Promise<SkillMetadata> {
  if (!metadataCache.has(skillName)) {
    metadataCache.set(skillName, await loader.getSkillMetadata(skillName));
  }
  return metadataCache.get(skillName)!;
}
```

### 3. Set Execution Timeouts

```typescript
async function executeWithTimeout(
  loader: SkillLoader,
  skillName: string,
  script: string,
  input: unknown,
  timeoutMs: number = 30000
): Promise<SkillExecutionResult> {
  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => reject(new Error('Skill execution timeout')), timeoutMs);
  });

  return Promise.race([
    loader.executeSkill(skillName, script, input),
    timeoutPromise,
  ]);
}
```

### 4. Log Skill Executions

```typescript
async function executeAndLog(
  loader: SkillLoader,
  skillName: string,
  script: string,
  input: unknown
): Promise<SkillExecutionResult> {
  const startTime = Date.now();

  console.log(`[SKILL] Executing ${skillName}/${script}`);

  const result = await loader.executeSkill(skillName, script, input);

  console.log(`[SKILL] ${skillName} completed in ${result.metadata.executionTimeMs}ms`, {
    success: result.success,
    skill: skillName,
    version: result.metadata.version,
  });

  return result;
}
```

### 5. Use Type-Safe Wrappers

```typescript
interface LCOEInput {
  technology?: string;
  capacity_mw?: number;
  capex_usd: number;
  annual_opex_usd?: number;
  annual_generation_mwh: number;
  project_lifetime_years: number;
  discount_rate: number;
  degradation_rate?: number;
}

interface LCOEOutput {
  lcoe_usd_per_mwh: number;
  lcoe_usd_per_kwh: number;
  total_lifecycle_cost_usd: number;
  npv_generation_mwh: number;
  annual_breakdown: Array<{
    year: number;
    generation_mwh: number;
    total_cost_usd: number;
  }>;
}

async function calculateLCOE(input: LCOEInput): Promise<LCOEOutput> {
  const result = await loader.executeSkill('lcoe-calculator', 'calculate_lcoe.py', input);

  if (!result.success) {
    throw new Error(result.error?.message || 'LCOE calculation failed');
  }

  return result.data as LCOEOutput;
}
```

---

## Next Steps

- **Explore the Skills**: Check the [lcoe-calculator](../lcoe-calculator/) reference implementation
- **Contribute**: Read the [Skill Development Guide](./SKILL_DEVELOPMENT_GUIDE.md) to add new skills
- **Join the Community**: Discuss on [GitHub Discussions](https://github.com/GreenCIO-AI/energy-transition-skills/discussions)

---

*This guide is part of the Energy Transition Skills library. For questions or feedback, please open an issue on GitHub.*
