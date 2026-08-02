#!/usr/bin/env python3
"""Record and assemble deterministic comprehensive-quality reports."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = Path(__file__).with_name("comparison-contract.json")
FINDING_FIELDS = (
    "category",
    "severity",
    "route_or_file",
    "viewport",
    "evidence",
    "reproduction",
    "safe_for_automated_remediation",
    "needs_review",
)
COMPONENT_ORDER = (
    "clean_build_and_browserless_tests",
    "automated_browser_ux_accessibility",
    "runtime_performance",
    "static_output_and_bloat_inventory",
    "human_ux_review",
)


def read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def component_status(report: dict[str, Any] | None, browser: bool = False) -> str:
    if report is None:
        return "NOT RUN"
    if report.get("status") in {"PASS", "FAIL", "PENDING", "NOT RUN"}:
        return str(report["status"])
    if browser and isinstance(report.get("summary"), dict):
        return "PASS" if report["summary"].get("passed") else "FAIL"
    return "FAIL"


def validate_finding(finding: dict[str, Any]) -> None:
    missing = [field for field in FINDING_FIELDS if field not in finding]
    if missing:
        raise ValueError(f"Finding is missing required fields {missing}: {finding}")


def normalized_findings(reports: list[dict[str, Any] | None]) -> list[dict[str, Any]]:
    unique = {}
    for report in reports:
        for finding in (report or {}).get("findings", []):
            validate_finding(finding)
            key = json.dumps(finding, sort_keys=True, ensure_ascii=False)
            unique[key] = finding
    return sorted(
        unique.values(),
        key=lambda item: (
            str(item["category"]),
            str(item["severity"]),
            str(item["route_or_file"]),
            str(item["evidence"]),
        ),
    )


def browser_metrics(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {}
    summary = report.get("summary", {})
    return {
        "browser.pages": summary.get("pages", report.get("pages")),
        "browser.checks": summary.get("checks", report.get("checks")),
        "browser.failures": summary.get("failures", len(report.get("failures", []))),
        "browser.console_messages": summary.get(
            "consoleMessages", len(report.get("consoleMessages", []))
        ),
        "browser.duration_ms": summary.get("durationMs", report.get("durationMs")),
        "browser.screenshot_count": len(report.get("screenshots", [])),
    }


def static_metrics(report: dict[str, Any] | None) -> dict[str, Any]:
    counts = (report or {}).get("counts", {})
    return {
        "static.source_file_count": counts.get("source_files"),
        "static.rendered_file_count": counts.get("rendered_files"),
        "static.duplicate_group_count": counts.get("duplicate_groups"),
        "static.module_review_candidate_count": counts.get("module_review_candidates"),
        "static.unreferenced_site_asset_count": counts.get("unreferenced_site_assets"),
    }


def build_metrics(report: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "build.clean_duration_ms": (report or {}).get("duration_ms"),
        "build.rendered_file_count": (report or {}).get("rendered_file_count"),
    }


def portable_evidence_path(
    path: Path | None, report: dict[str, Any] | None, output_dir: Path
) -> str | None:
    if path is None or report is None:
        return None
    try:
        return Path(os.path.relpath(path.resolve(), output_dir.resolve())).as_posix()
    except ValueError:
        return path.as_posix()


def assemble(
    *,
    output_dir: Path,
    contract_path: Path,
    build_path: Path | None,
    browser_path: Path | None,
    performance_path: Path | None,
    static_path: Path | None,
) -> dict[str, Any]:
    contract = read_json(contract_path)
    if contract is None:
        raise FileNotFoundError(contract_path)
    build = read_json(build_path)
    browser = read_json(browser_path)
    performance = read_json(performance_path)
    static = read_json(static_path)
    components = {
        "clean_build_and_browserless_tests": {
            "status": component_status(build),
            "evidence": portable_evidence_path(build_path, build, output_dir),
        },
        "automated_browser_ux_accessibility": {
            "status": component_status(browser, browser=True),
            "evidence": portable_evidence_path(browser_path, browser, output_dir),
        },
        "runtime_performance": {
            "status": component_status(performance),
            "evidence": portable_evidence_path(
                performance_path, performance, output_dir
            ),
        },
        "static_output_and_bloat_inventory": {
            "status": component_status(static),
            "evidence": portable_evidence_path(static_path, static, output_dir),
        },
        "human_ux_review": {
            "status": "NOT RUN",
            "evidence": None,
        },
    }
    automated = [components[name]["status"] for name in COMPONENT_ORDER[:-1]]
    overall = "FAIL" if "FAIL" in automated else "PASS" if all(
        status == "PASS" for status in automated
    ) else "PARTIAL"
    findings = normalized_findings([build, browser, performance, static])
    metrics = {}
    metrics.update(build_metrics(build))
    metrics.update(browser_metrics(browser))
    metrics.update(static_metrics(static))
    metrics["performance.measurements"] = (performance or {}).get("measurements")
    metrics["performance.interactions"] = (performance or {}).get("interactions")
    screenshots = sorted(
        (browser or {}).get("screenshots", []),
        key=lambda item: (str(item.get("kind")), str(item.get("viewport")), str(item.get("page"))),
    )
    baseline = {
        "schema_version": 1,
        "overall_status": overall,
        "comparison_contract": contract,
        "components": components,
        "metrics": metrics,
        "reliability": (performance or {}).get("reliability", {}),
        "screenshots": screenshots,
        "source_reports": {
            "build": build,
            "browser": browser,
            "performance": performance,
            "static": static,
        },
    }
    finding_document = {"schema_version": 1, "findings": findings}
    write_json(output_dir / "baseline.json", baseline)
    write_json(output_dir / "findings.json", finding_document)
    category_counts = Counter(item["category"] for item in findings)
    severity_counts = Counter(item["severity"] for item in findings)
    lines = [
        "# Comprehensive quality baseline",
        "",
        f"Overall automated status: **{overall}**",
        "",
        "## Independent component statuses",
        "",
        "| Component | Status |",
        "| --- | --- |",
    ]
    for name in COMPONENT_ORDER:
        lines.append(f"| {name.replace('_', ' ')} | {components[name]['status']} |")
    lines.extend(
        [
            "",
            "Human UX review is intentionally `NOT RUN`; no automated result can pass it.",
            "",
            "## Baseline metrics",
            "",
            f"- Clean build duration: {metrics.get('build.clean_duration_ms')} ms",
            f"- Rendered file count: {metrics.get('build.rendered_file_count')}",
            f"- Browser pages/checks/failures: {metrics.get('browser.pages')}/{metrics.get('browser.checks')}/{metrics.get('browser.failures')}",
            f"- Baseline and failure screenshots: {len(screenshots)}",
            f"- Static duplicate groups: {metrics.get('static.duplicate_group_count')}",
            f"- Static unreferenced-site-asset candidates: {metrics.get('static.unreferenced_site_asset_count')}",
            "",
            "## Findings",
            "",
            f"Total findings: {len(findings)}",
            "",
            f"Categories: {json.dumps(dict(sorted(category_counts.items())), sort_keys=True)}",
            "",
            f"Severities: {json.dumps(dict(sorted(severity_counts.items())), sort_keys=True)}",
            "",
            "The static reference scan is evidence, not deletion proof. No product defect, simplification, or archive candidate was remediated in this baseline task.",
            "",
            "## Comparison contract",
            "",
            "The complete routes, viewports, repetitions, metric names, commands, screenshot bounds, and report schema are embedded unchanged in `baseline.json` from `scripts/testing/quality/comparison-contract.json`.",
            "",
        ]
    )
    (output_dir / "baseline-summary.md").write_text("\n".join(lines), encoding="utf-8")
    return baseline


def record_build(args: argparse.Namespace) -> int:
    write_json(
        args.output,
        {
            "schema_version": 1,
            "status": args.status,
            "command": args.command,
            "duration_ms": args.duration_ms,
            "rendered_file_count": args.rendered_file_count,
            "findings": [],
        },
    )
    return 0


def record_component(args: argparse.Namespace) -> int:
    write_json(
        args.output,
        {
            "schema_version": 1,
            "status": args.status,
            "evidence": args.evidence,
            "findings": [
                {
                    "category": "test-infrastructure",
                    "severity": "blocking",
                    "route_or_file": args.route_or_file,
                    "viewport": None,
                    "evidence": args.evidence,
                    "reproduction": args.reproduction,
                    "safe_for_automated_remediation": False,
                    "needs_review": True,
                }
            ]
            if args.status == "FAIL"
            else [],
        },
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    build = subparsers.add_parser("record-build")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--status", choices=("PASS", "FAIL"), required=True)
    build.add_argument("--command", required=True)
    build.add_argument("--duration-ms", type=int, required=True)
    build.add_argument("--rendered-file-count", type=int, required=True)
    component = subparsers.add_parser("record-component")
    component.add_argument("--output", type=Path, required=True)
    component.add_argument("--status", choices=("PASS", "FAIL", "NOT RUN"), required=True)
    component.add_argument("--route-or-file", required=True)
    component.add_argument("--evidence", required=True)
    component.add_argument("--reproduction", required=True)
    assemble_parser = subparsers.add_parser("assemble")
    assemble_parser.add_argument("--output-dir", type=Path, required=True)
    assemble_parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    assemble_parser.add_argument("--build", type=Path)
    assemble_parser.add_argument("--browser", type=Path)
    assemble_parser.add_argument("--performance", type=Path)
    assemble_parser.add_argument("--static", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "record-build":
        return record_build(args)
    if args.action == "record-component":
        return record_component(args)
    baseline = assemble(
        output_dir=args.output_dir,
        contract_path=args.contract,
        build_path=args.build,
        browser_path=args.browser,
        performance_path=args.performance,
        static_path=args.static,
    )
    print(f"Comprehensive quality baseline: {baseline['overall_status']}")
    return 1 if baseline["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
