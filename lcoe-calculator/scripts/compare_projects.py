#!/usr/bin/env python3
"""
LCOE Project Comparator

Compare LCOE across multiple energy projects to support investment decisions.
Provides ranking, relative analysis, and recommendation insights.

Usage:
    python compare_projects.py --inputs solar.json wind.json gas.json
    python compare_projects.py --inputs-dir projects/
    cat projects_array.json | python compare_projects.py

No external dependencies - uses only Python standard library.
"""

import json
import sys
import argparse
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from calculate_lcoe import validate_input, calculate_lcoe, LCOEInput

VERSION = "1.0.0"
SKILL_NAME = "lcoe-calculator"


def load_projects(
    input_files: Optional[List[str]] = None,
    input_dir: Optional[str] = None,
    stdin_data: Optional[List[Dict]] = None
) -> List[Dict[str, Any]]:
    """Load project configurations from various sources."""
    projects = []

    if stdin_data:
        for i, proj in enumerate(stdin_data):
            proj["_source"] = f"stdin_project_{i+1}"
            projects.append(proj)

    if input_files:
        for filepath in input_files:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    data["_source"] = filepath
                    projects.append(data)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not load {filepath}: {e}", file=sys.stderr)

    if input_dir:
        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(input_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        data["_source"] = filepath
                        projects.append(data)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Warning: Could not load {filepath}: {e}", file=sys.stderr)

    return projects


def analyze_project(project: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single project and return results with metadata."""
    source = project.pop("_source", "unknown")

    validated = validate_input(project)
    if "code" in validated:
        return {
            "source": source,
            "success": False,
            "error": validated,
            "technology": project.get("technology", "unknown")
        }

    result = calculate_lcoe(validated)
    return {
        "source": source,
        "success": True,
        "technology": validated.get("technology", "generic"),
        "capacity_mw": validated.get("capacity_mw"),
        "lcoe_usd_per_mwh": result["lcoe_usd_per_mwh"],
        "lcoe_usd_per_kwh": result["lcoe_usd_per_kwh"],
        "lcoe_cents_per_kwh": result["lcoe_cents_per_kwh"],
        "capex_usd": validated["capex_usd"],
        "capex_per_mw": (
            validated["capex_usd"] / validated["capacity_mw"]
            if validated.get("capacity_mw") else None
        ),
        "project_lifetime_years": validated["project_lifetime_years"],
        "total_lifecycle_cost_usd": result["total_lifecycle_cost_usd"],
        "total_lifetime_generation_mwh": result["total_lifetime_generation_mwh"],
        "npv_costs_usd": result["npv_costs_usd"],
        "capacity_factor": result.get("capacity_factor"),
        "discount_rate": validated["discount_rate"]
    }


def compare_projects(projects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare multiple projects and provide analysis."""
    # Analyze each project
    analyzed = [analyze_project(p.copy()) for p in projects]

    # Separate successful and failed analyses
    successful = [a for a in analyzed if a["success"]]
    failed = [a for a in analyzed if not a["success"]]

    if not successful:
        return {
            "success": False,
            "error": {
                "code": "NO_VALID_PROJECTS",
                "message": "No projects could be analyzed successfully"
            },
            "failed_projects": failed
        }

    # Sort by LCOE
    ranked = sorted(successful, key=lambda x: x["lcoe_usd_per_mwh"])

    # Add ranking
    for i, proj in enumerate(ranked):
        proj["rank"] = i + 1

    # Calculate statistics
    lcoes = [p["lcoe_usd_per_mwh"] for p in successful]
    avg_lcoe = sum(lcoes) / len(lcoes)
    min_lcoe = min(lcoes)
    max_lcoe = max(lcoes)

    # Best project
    best = ranked[0]

    # Calculate relative metrics
    for proj in ranked:
        proj["lcoe_vs_best_pct"] = round(
            (proj["lcoe_usd_per_mwh"] - best["lcoe_usd_per_mwh"]) /
            best["lcoe_usd_per_mwh"] * 100, 1
        ) if best["lcoe_usd_per_mwh"] > 0 else 0

        proj["lcoe_vs_avg_pct"] = round(
            (proj["lcoe_usd_per_mwh"] - avg_lcoe) / avg_lcoe * 100, 1
        ) if avg_lcoe > 0 else 0

    # Group by technology
    by_technology = {}
    for proj in successful:
        tech = proj["technology"]
        if tech not in by_technology:
            by_technology[tech] = []
        by_technology[tech].append(proj)

    # Technology summary
    tech_summary = {}
    for tech, tech_projects in by_technology.items():
        tech_lcoes = [p["lcoe_usd_per_mwh"] for p in tech_projects]
        tech_summary[tech] = {
            "count": len(tech_projects),
            "avg_lcoe_usd_per_mwh": round(sum(tech_lcoes) / len(tech_lcoes), 2),
            "min_lcoe_usd_per_mwh": round(min(tech_lcoes), 2),
            "max_lcoe_usd_per_mwh": round(max(tech_lcoes), 2),
            "best_project": min(tech_projects, key=lambda x: x["lcoe_usd_per_mwh"])["source"]
        }

    # Generate recommendations
    recommendations = generate_recommendations(ranked, tech_summary)

    return {
        "success": True,
        "summary": {
            "total_projects": len(projects),
            "analyzed_successfully": len(successful),
            "failed_to_analyze": len(failed),
            "best_project": {
                "source": best["source"],
                "technology": best["technology"],
                "lcoe_usd_per_mwh": best["lcoe_usd_per_mwh"]
            },
            "statistics": {
                "avg_lcoe_usd_per_mwh": round(avg_lcoe, 2),
                "min_lcoe_usd_per_mwh": round(min_lcoe, 2),
                "max_lcoe_usd_per_mwh": round(max_lcoe, 2),
                "lcoe_spread_usd_per_mwh": round(max_lcoe - min_lcoe, 2),
                "lcoe_spread_pct": round((max_lcoe - min_lcoe) / min_lcoe * 100, 1) if min_lcoe > 0 else 0
            }
        },
        "by_technology": tech_summary,
        "rankings": ranked,
        "recommendations": recommendations,
        "failed_projects": failed if failed else None
    }


def generate_recommendations(
    ranked: List[Dict[str, Any]],
    tech_summary: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate actionable recommendations from comparison."""
    recommendations = []

    if not ranked:
        return recommendations

    best = ranked[0]
    worst = ranked[-1]

    # Best project recommendation
    recommendations.append({
        "priority": "HIGH",
        "type": "INVESTMENT",
        "title": f"Prioritize {best['technology']} project",
        "description": (
            f"'{best['source']}' has the lowest LCOE at ${best['lcoe_usd_per_mwh']}/MWh. "
            f"This represents the most cost-effective option among analyzed projects."
        ),
        "impact": {
            "lcoe_advantage_vs_worst": f"${round(worst['lcoe_usd_per_mwh'] - best['lcoe_usd_per_mwh'], 2)}/MWh",
            "percentage_better": f"{round((worst['lcoe_usd_per_mwh'] - best['lcoe_usd_per_mwh']) / worst['lcoe_usd_per_mwh'] * 100, 1)}%"
        }
    })

    # Technology diversification
    if len(tech_summary) > 1:
        tech_lcoes = [(t, s["avg_lcoe_usd_per_mwh"]) for t, s in tech_summary.items()]
        tech_lcoes.sort(key=lambda x: x[1])
        best_tech, best_tech_lcoe = tech_lcoes[0]
        worst_tech, worst_tech_lcoe = tech_lcoes[-1]

        if worst_tech_lcoe > best_tech_lcoe * 1.2:  # >20% more expensive
            recommendations.append({
                "priority": "MEDIUM",
                "type": "PORTFOLIO",
                "title": f"Review {worst_tech} allocation",
                "description": (
                    f"{worst_tech} projects average ${round(worst_tech_lcoe, 2)}/MWh, "
                    f"which is {round((worst_tech_lcoe - best_tech_lcoe) / best_tech_lcoe * 100, 1)}% "
                    f"higher than {best_tech}. Consider rebalancing portfolio mix."
                ),
                "impact": {
                    "potential_savings": f"Up to ${round(worst_tech_lcoe - best_tech_lcoe, 2)}/MWh by shifting allocation"
                }
            })

    # High-cost outliers
    avg_lcoe = sum(p["lcoe_usd_per_mwh"] for p in ranked) / len(ranked)
    outliers = [p for p in ranked if p["lcoe_usd_per_mwh"] > avg_lcoe * 1.3]

    if outliers:
        recommendations.append({
            "priority": "MEDIUM",
            "type": "REVIEW",
            "title": f"Investigate high-cost outliers ({len(outliers)} projects)",
            "description": (
                f"The following projects are >30% above average LCOE and may warrant "
                f"renegotiation or divestiture: {', '.join(p['source'] for p in outliers)}"
            ),
            "projects": [p["source"] for p in outliers]
        })

    return recommendations


def main():
    parser = argparse.ArgumentParser(
        description="Compare LCOE across multiple projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare specific files
  python compare_projects.py --inputs solar.json wind.json gas.json

  # Compare all JSON files in directory
  python compare_projects.py --inputs-dir projects/

  # Compare from stdin (array of projects)
  cat projects.json | python compare_projects.py
        """
    )
    parser.add_argument(
        "--inputs", "-i",
        nargs="+",
        type=str,
        help="Input JSON files to compare"
    )
    parser.add_argument(
        "--inputs-dir", "-d",
        type=str,
        help="Directory containing project JSON files"
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

    # Check for stdin input
    stdin_data = None
    if not sys.stdin.isatty():
        try:
            stdin_data = json.load(sys.stdin)
            if not isinstance(stdin_data, list):
                stdin_data = [stdin_data]
        except json.JSONDecodeError:
            pass

    # Load projects
    projects = load_projects(
        input_files=args.inputs,
        input_dir=args.inputs_dir,
        stdin_data=stdin_data
    )

    if not projects:
        output = {
            "success": False,
            "error": {
                "code": "NO_INPUT",
                "message": "No project files provided. Use --inputs, --inputs-dir, or stdin."
            }
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)

    # Compare projects
    results = compare_projects(projects)

    # Add metadata
    output = {
        **results,
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
