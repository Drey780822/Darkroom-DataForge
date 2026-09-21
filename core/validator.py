from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from models.dataset import Dataset
from models.record import Record
from models.validation import (
    ValidationRule,
    ValidationIssue,
    IssueSeverity,
    ValidationSummary,
)


class Validator:
    """Rule-based data validation engine enforcing schema constraints and integrity."""

    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        self.rules: List[ValidationRule] = rules or []

    def add_rule(self, rule: ValidationRule) -> None:
        self.rules.append(rule)

    def generate_default_rules(self, dataset: Dataset) -> List[ValidationRule]:
        rules: List[ValidationRule] = []

        for col in dataset.columns:
            # 1. Required rule for primary keys or required fields
            if col.required or col.is_primary_key:
                rules.append(
                    ValidationRule(
                        id=f"req_{col.name}",
                        name=f"Required field: {col.display_name}",
                        field_name=col.name,
                        rule_type="required",
                        severity=IssueSeverity.CRITICAL,
                    )
                )

            # 2. Specific pattern for SAQA ID (numeric, 5-7 digits)
            if "saqa" in col.name:
                rules.append(
                    ValidationRule(
                        id=f"saqa_regex_{col.name}",
                        name="SAQA ID must be 4–7 numeric digits",
                        field_name=col.name,
                        rule_type="regex",
                        severity=IssueSeverity.CRITICAL,
                        parameters={"pattern": r"^\d{4,7}$"},
                    )
                )

            # 3. Specific pattern for OFO Code (numeric, 4-6 digits)
            if "ofo" in col.name:
                rules.append(
                    ValidationRule(
                        id=f"ofo_regex_{col.name}",
                        name="OFO Code must be 4–6 numeric digits",
                        field_name=col.name,
                        rule_type="regex",
                        severity=IssueSeverity.CRITICAL,
                        parameters={"pattern": r"^\d{4,6}$"},
                    )
                )

            # 4. Range rule for NQF level (1 to 10)
            if "nqf" in col.name:
                rules.append(
                    ValidationRule(
                        id=f"nqf_range_{col.name}",
                        name="NQF Level must be between 1 and 10",
                        field_name=col.name,
                        rule_type="range",
                        severity=IssueSeverity.CRITICAL,
                        parameters={"min": 1, "max": 10},
                    )
                )

        return rules

    def validate_dataset(self, dataset: Dataset) -> ValidationSummary:
        issues: List[ValidationIssue] = []
        rules_to_run = self.rules if self.rules else self.generate_default_rules(dataset)
        records_with_issues = set()

        for rec in dataset.records:
            for rule in rules_to_run:
                val = rec.get_value(rule.field_name, prefer_normalized=True)

                if rule.rule_type == "required":
                    if val is None or str(val).strip() == "":
                        issue = ValidationIssue(
                            record_id=rec.id,
                            field_name=rule.field_name,
                            severity=rule.severity,
                            rule_name=rule.name,
                            message=f"Missing required value for '{rule.field_name}'",
                            current_value=val,
                            source_page=rec.provenance.source_page,
                            source_document=rec.provenance.source_document,
                        )
                        issues.append(issue)
                        records_with_issues.add(rec.id)
                        rec.is_flagged_for_review = True

                elif rule.rule_type == "regex" and val is not None:
                    pattern = rule.parameters.get("pattern", "")
                    val_str = str(val).strip()
                    if pattern and not re.match(pattern, val_str):
                        # Check if auto-fixable (e.g. whitespace or non-digit noise)
                        cleaned_digits = re.sub(r"\D", "", val_str)
                        can_auto_fix = bool(pattern and re.match(pattern, cleaned_digits))

                        issue = ValidationIssue(
                            record_id=rec.id,
                            field_name=rule.field_name,
                            severity=rule.severity,
                            rule_name=rule.name,
                            message=f"Value '{val_str}' does not match expected format",
                            current_value=val,
                            suggested_fix=cleaned_digits if can_auto_fix else None,
                            is_auto_fixable=can_auto_fix,
                            source_page=rec.provenance.source_page,
                            source_document=rec.provenance.source_document,
                        )
                        issues.append(issue)
                        records_with_issues.add(rec.id)
                        rec.is_flagged_for_review = True

                elif rule.rule_type == "range" and val is not None:
                    try:
                        num = float(val)
                        min_v = rule.parameters.get("min")
                        max_v = rule.parameters.get("max")
                        if (min_v is not None and num < min_v) or (max_v is not None and num > max_v):
                            issue = ValidationIssue(
                                record_id=rec.id,
                                field_name=rule.field_name,
                                severity=rule.severity,
                                rule_name=rule.name,
                                message=f"Value {num} outside valid range [{min_v}, {max_v}]",
                                current_value=val,
                                source_page=rec.provenance.source_page,
                                source_document=rec.provenance.source_document,
                            )
                            issues.append(issue)
                            records_with_issues.add(rec.id)
                            rec.is_flagged_for_review = True
                    except (ValueError, TypeError):
                        issue = ValidationIssue(
                            record_id=rec.id,
                            field_name=rule.field_name,
                            severity=IssueSeverity.WARNING,
                            rule_name=rule.name,
                            message=f"Value '{val}' is not numeric for range check",
                            current_value=val,
                            source_page=rec.provenance.source_page,
                            source_document=rec.provenance.source_document,
                        )
                        issues.append(issue)
                        records_with_issues.add(rec.id)
                        rec.is_flagged_for_review = True

        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        info_count = sum(1 for i in issues if i.severity == IssueSeverity.INFO)
        auto_fixable = sum(1 for i in issues if i.is_auto_fixable and not i.is_fixed)

        return ValidationSummary(
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            total_issues=len(issues),
            records_with_issues=len(records_with_issues),
            auto_fixable_count=auto_fixable,
            issues=issues,
        )

    def apply_auto_fixes(self, dataset: Dataset, summary: ValidationSummary) -> int:
        """Deterministically fixes auto-fixable issues."""
        fixed_count = 0
        rec_map = {r.id: r for r in dataset.records}

        for issue in summary.issues:
            if issue.is_auto_fixable and not issue.is_fixed and issue.suggested_fix is not None:
                rec = rec_map.get(issue.record_id)
                if rec and issue.field_name in rec.cells:
                    rec.set_value(issue.field_name, rec.cells[issue.field_name].raw_value, issue.suggested_fix)
                    issue.is_fixed = True
                    fixed_count += 1

        return fixed_count
