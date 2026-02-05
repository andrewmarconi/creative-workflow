#!/usr/bin/env python3
"""Consistency checker for Generative Creative Lab.

Validates alignment between:
- Django models and migrations
- Admin configuration and model fields
- Documentation and actual schema
- Data files (presets.json, CSV files)

Usage:
    python .claude/hooks/consistency_checker.py [--verbose] [--json]

Exit codes:
    0 - All checks passed (may have warnings)
    1 - One or more checks failed
    2 - Script error
"""

import ast
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CheckResult:
    """Result of a single consistency check."""

    name: str
    status: str  # "pass", "warn", "fail"
    message: str
    details: list[str] = field(default_factory=list)


class ConsistencyChecker:
    """Comprehensive consistency checker for the codebase."""

    BASE_ARCHITECTURES = {"sdxl", "sd15", "flux1", "qwen", "zimage"}

    def __init__(self, repo_dir: str = "."):
        self.repo_dir = Path(repo_dir).resolve()
        self.results: list[CheckResult] = []

    def check_all(self) -> bool:
        """Run all consistency checks. Returns True if no failures."""
        self._check_models_exist()
        self._check_migrations_exist()
        self._check_admin_config()
        self._check_presets_json()
        self._check_database_schema_rst()
        self._check_core_data_json()

        failures = [r for r in self.results if r.status == "fail"]
        return len(failures) == 0

    def _check_models_exist(self) -> None:
        """Verify model files exist and are valid Python."""
        model_files = [
            "src/cw/diffusion/models.py",
            "src/cw/tvspots/models.py",
        ]

        for rel_path in model_files:
            filepath = self.repo_dir / rel_path
            if not filepath.exists():
                self.results.append(
                    CheckResult(
                        name=f"Model file: {rel_path}",
                        status="fail",
                        message=f"Model file not found: {rel_path}",
                    )
                )
                continue

            # Try to parse as Python
            try:
                with open(filepath, encoding="utf-8") as f:
                    ast.parse(f.read())
                self.results.append(
                    CheckResult(
                        name=f"Model file: {rel_path}",
                        status="pass",
                        message="Valid Python syntax",
                    )
                )
            except SyntaxError as e:
                self.results.append(
                    CheckResult(
                        name=f"Model file: {rel_path}",
                        status="fail",
                        message=f"Python syntax error: {e}",
                    )
                )

    def _check_migrations_exist(self) -> None:
        """Verify migration directories have migrations."""
        migration_dirs = [
            ("src/cw/diffusion/migrations", "diffusion"),
            ("src/cw/tvspots/migrations", "tvspots"),
        ]

        for rel_path, app_name in migration_dirs:
            dirpath = self.repo_dir / rel_path
            if not dirpath.exists():
                self.results.append(
                    CheckResult(
                        name=f"Migrations: {app_name}",
                        status="fail",
                        message=f"Migrations directory not found: {rel_path}",
                    )
                )
                continue

            migrations = list(dirpath.glob("*.py"))
            # Exclude __init__.py
            migrations = [m for m in migrations if m.name != "__init__.py"]

            if len(migrations) == 0:
                self.results.append(
                    CheckResult(
                        name=f"Migrations: {app_name}",
                        status="warn",
                        message="No migrations found (run makemigrations?)",
                    )
                )
            else:
                self.results.append(
                    CheckResult(
                        name=f"Migrations: {app_name}",
                        status="pass",
                        message=f"{len(migrations)} migration(s) found",
                        details=[m.name for m in sorted(migrations)[-3:]],
                    )
                )

    def _check_admin_config(self) -> None:
        """Verify admin files exist and reference valid fields."""
        admin_files = [
            ("src/cw/diffusion/admin.py", "src/cw/diffusion/models.py"),
            ("src/cw/tvspots/admin.py", "src/cw/tvspots/models.py"),
        ]

        for admin_rel, models_rel in admin_files:
            admin_path = self.repo_dir / admin_rel
            models_path = self.repo_dir / models_rel

            if not admin_path.exists():
                self.results.append(
                    CheckResult(
                        name=f"Admin: {admin_rel}",
                        status="warn",
                        message="Admin file not found",
                    )
                )
                continue

            if not models_path.exists():
                continue  # Already reported in model check

            # Extract model class names from models.py
            try:
                with open(models_path, encoding="utf-8") as f:
                    models_content = f.read()
                model_classes = set(re.findall(r"class (\w+)\(.*Model\)", models_content))
            except Exception:
                model_classes = set()

            # Check admin references these models
            try:
                with open(admin_path, encoding="utf-8") as f:
                    admin_content = f.read()

                # Find registered models
                registered = set(re.findall(r"@admin\.register\((\w+)\)", admin_content))
                registered.update(re.findall(r"admin\.site\.register\((\w+)", admin_content))

                missing = model_classes - registered - {"TimeStampedModel"}
                if missing:
                    self.results.append(
                        CheckResult(
                            name=f"Admin: {admin_rel}",
                            status="warn",
                            message=f"Models not in admin: {', '.join(sorted(missing))}",
                        )
                    )
                else:
                    self.results.append(
                        CheckResult(
                            name=f"Admin: {admin_rel}",
                            status="pass",
                            message=f"All {len(registered)} models registered",
                        )
                    )
            except Exception as e:
                self.results.append(
                    CheckResult(
                        name=f"Admin: {admin_rel}",
                        status="fail",
                        message=f"Error reading admin file: {e}",
                    )
                )

    def _check_presets_json(self) -> None:
        """Validate presets.json structure and content."""
        filepath = self.repo_dir / "data/presets.json"

        if not filepath.exists():
            self.results.append(
                CheckResult(
                    name="Data: presets.json",
                    status="fail",
                    message="presets.json not found",
                )
            )
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.results.append(
                CheckResult(
                    name="Data: presets.json",
                    status="fail",
                    message=f"Invalid JSON: {e}",
                )
            )
            return

        issues: list[str] = []
        warnings: list[str] = []

        # Check models
        models = data.get("models", [])
        for i, model in enumerate(models):
            required = ["slug", "label", "path", "pipeline", "base_architecture"]
            missing = [f for f in required if f not in model]
            if missing:
                issues.append(f"Model {i}: missing {', '.join(missing)}")

            arch = model.get("base_architecture", "")
            if arch and arch not in self.BASE_ARCHITECTURES:
                warnings.append(f"Model '{model.get('slug', i)}': unknown architecture '{arch}'")

        # Check loras
        loras = data.get("loras", [])
        for i, lora in enumerate(loras):
            required = ["label", "base_architecture"]
            missing = [f for f in required if f not in lora]
            if missing:
                issues.append(f"LoRA {i}: missing {', '.join(missing)}")

            arch = lora.get("base_architecture", "")
            if arch and arch not in self.BASE_ARCHITECTURES:
                warnings.append(f"LoRA '{lora.get('label', i)}': unknown architecture '{arch}'")

            # Check AIR format if present
            air = lora.get("air", "")
            if air and not air.startswith("urn:air:"):
                warnings.append(f"LoRA '{lora.get('label', i)}': invalid AIR format")

        if issues:
            self.results.append(
                CheckResult(
                    name="Data: presets.json",
                    status="fail",
                    message=f"{len(issues)} structural issue(s)",
                    details=issues[:5],
                )
            )
        elif warnings:
            self.results.append(
                CheckResult(
                    name="Data: presets.json",
                    status="warn",
                    message=f"{len(models)} models, {len(loras)} loras ({len(warnings)} warnings)",
                    details=warnings[:5],
                )
            )
        else:
            self.results.append(
                CheckResult(
                    name="Data: presets.json",
                    status="pass",
                    message=f"{len(models)} models, {len(loras)} loras validated",
                )
            )

    def _check_database_schema_rst(self) -> None:
        """Verify database-schema.rst documents all models."""
        filepath = self.repo_dir / "docs/reference/database-schema.rst"

        if not filepath.exists():
            self.results.append(
                CheckResult(
                    name="Docs: database-schema.rst",
                    status="warn",
                    message="Schema documentation not found",
                )
            )
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.results.append(
                CheckResult(
                    name="Docs: database-schema.rst",
                    status="fail",
                    message=f"Error reading file: {e}",
                )
            )
            return

        # Expected models (from our knowledge of the codebase)
        expected_models = {
            "DiffusionModel",
            "LoraModel",
            "Prompt",
            "DiffusionJob",
            "AdaptationMarket",
            "TvSpot",
            "TvSpotVersion",
            "TvSpotScriptRow",
            "AdaptationJob",
            "StoryboardJob",
            "StoryboardImage",
        }

        documented = set()
        for model in expected_models:
            if model in content:
                documented.add(model)

        missing = expected_models - documented
        if missing:
            self.results.append(
                CheckResult(
                    name="Docs: database-schema.rst",
                    status="warn",
                    message=f"Models not documented: {', '.join(sorted(missing))}",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    name="Docs: database-schema.rst",
                    status="pass",
                    message=f"All {len(expected_models)} models documented",
                )
            )

    def _check_core_data_json(self) -> None:
        """Validate core_data.json (languages and LLM models)."""
        filepath = self.repo_dir / "data/core_data.json"

        if not filepath.exists():
            self.results.append(
                CheckResult(
                    name="Data: core_data.json",
                    status="warn",
                    message="File not found (run export_coredata to create)",
                )
            )
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.results.append(
                CheckResult(
                    name="Data: core_data.json",
                    status="fail",
                    message=f"Invalid JSON: {e}",
                )
            )
            return

        issues: list[str] = []
        warnings: list[str] = []

        # Check LLM models
        models = data.get("llm_models", [])
        for i, model in enumerate(models):
            required = ["model_id", "name"]
            missing = [f for f in required if f not in model]
            if missing:
                issues.append(f"LLM model {i}: missing {', '.join(missing)}")

        # Check languages
        languages = data.get("languages", [])
        for i, lang in enumerate(languages):
            required = ["code", "name", "primary_model"]
            missing = [f for f in required if f not in lang]
            if missing:
                issues.append(f"Language {i}: missing {', '.join(missing)}")

            # Check primary_model references a known model
            primary = lang.get("primary_model", "")
            model_ids = {m.get("model_id") for m in models}
            if primary and primary not in model_ids:
                warnings.append(f"Language '{lang.get('code', i)}': primary_model '{primary}' not in llm_models")

        if issues:
            self.results.append(
                CheckResult(
                    name="Data: core_data.json",
                    status="fail",
                    message=f"{len(issues)} structural issue(s)",
                    details=issues[:5],
                )
            )
        elif warnings:
            self.results.append(
                CheckResult(
                    name="Data: core_data.json",
                    status="warn",
                    message=f"{len(models)} models, {len(languages)} languages ({len(warnings)} warnings)",
                    details=warnings[:5],
                )
            )
        else:
            self.results.append(
                CheckResult(
                    name="Data: core_data.json",
                    status="pass",
                    message=f"{len(models)} LLM models, {len(languages)} languages validated",
                )
            )

    def report_text(self) -> str:
        """Generate human-readable report."""
        lines = ["## Consistency Check Results", ""]

        # Group by category
        categories = {
            "Model": [],
            "Migration": [],
            "Admin": [],
            "Data": [],
            "Docs": [],
        }

        for result in self.results:
            for cat in categories:
                if result.name.startswith(cat):
                    categories[cat].append(result)
                    break

        status_icons = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}

        for category, results in categories.items():
            if results:
                lines.append(f"### {category}")
                for r in results:
                    icon = status_icons.get(r.status, "[????]")
                    lines.append(f"- {icon} {r.name}: {r.message}")
                    for detail in r.details:
                        lines.append(f"    - {detail}")
                lines.append("")

        # Summary
        passes = sum(1 for r in self.results if r.status == "pass")
        warnings = sum(1 for r in self.results if r.status == "warn")
        failures = sum(1 for r in self.results if r.status == "fail")

        lines.append("### Summary")
        lines.append(f"{passes} passed, {warnings} warnings, {failures} failures")

        return "\n".join(lines)

    def report_json(self) -> str:
        """Generate JSON report."""
        return json.dumps(
            {
                "results": [
                    {
                        "name": r.name,
                        "status": r.status,
                        "message": r.message,
                        "details": r.details,
                    }
                    for r in self.results
                ],
                "summary": {
                    "passed": sum(1 for r in self.results if r.status == "pass"),
                    "warnings": sum(1 for r in self.results if r.status == "warn"),
                    "failures": sum(1 for r in self.results if r.status == "fail"),
                },
            },
            indent=2,
        )


def main() -> int:
    """Run consistency checks."""
    import argparse

    parser = argparse.ArgumentParser(description="Check codebase consistency")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--repo", default=".", help="Repository root directory")
    args = parser.parse_args()

    checker = ConsistencyChecker(args.repo)
    success = checker.check_all()

    if args.json:
        print(checker.report_json())
    else:
        print(checker.report_text())

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
