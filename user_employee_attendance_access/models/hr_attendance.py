# -*- coding: utf-8 -*-

from odoo import api, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model
    def action_open_my_allowed_attendance(self):
        """Open attendance of employees selected on the current user.

        The actual security is handled by ir.rule. This method only provides
        a clean menu action and forces all companies in context.
        """

        all_company_ids = self.env["res.company"].sudo().search([]).ids
        employee_ids = self.env.user.employee_ids.ids
        print(employee_ids,all_company_ids,"======================================")

        return {
            "type": "ir.actions.act_window",
            "name": "My Allowed Employee Attendances",
            "res_model": "hr.attendance",
            "view_mode": "tree,form,pivot,graph",
            "domain": [("employee_id", "in", employee_ids)],
            "context": {
                "allowed_company_ids": all_company_ids,
                "search_default_groupby_employee": 1,
            },
            "target": "current",
        }
