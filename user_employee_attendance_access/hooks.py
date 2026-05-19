# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Disable old hr.attendance rules so this module's selected-employee
    rule becomes the source of truth.

    Also disable company-based hr.employee rules so the user employee_ids
    selection can show employees from all companies.

    We intentionally do not delete any rule. We only make them inactive.
    """

    IrRule = env["ir.rule"].sudo()

    custom_rules = env["ir.model.data"].sudo().search([
        ("module", "=", "mir_user_employee_attendance_access"),
        ("name", "in", [
            "rule_hr_attendance_user_selected_employees",
            "rule_hr_employee_all_companies_for_user_selection",
        ]),
        ("model", "=", "ir.rule"),
    ]).mapped("res_id")

    # Disable every existing hr.attendance rule except our own rule.
    attendance_rules = IrRule.search([
        ("model_id.model", "=", "hr.attendance"),
        ("id", "not in", custom_rules),
        ("active", "=", True),
    ])
    if attendance_rules:
        _logger.info(
            "MIR attendance access: disabling old hr.attendance rules: %s",
            attendance_rules.mapped("name"),
        )
        attendance_rules.write({"active": False})

    # Disable only company-based employee rules. This allows the M2M field
    # on users to list employees from every company.
    employee_company_rules = IrRule.search([
        ("model_id.model", "=", "hr.employee"),
        ("domain_force", "ilike", "company_id"),
        ("id", "not in", custom_rules),
        ("active", "=", True),
    ])
    if employee_company_rules:
        _logger.info(
            "MIR attendance access: disabling company-based hr.employee rules: %s",
            employee_company_rules.mapped("name"),
        )
        employee_company_rules.write({"active": False})
