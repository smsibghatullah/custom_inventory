# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="res_users_attendance_employee_rel",
        column1="user_id",
        column2="employee_id",
        string="Allowed Attendance Employees",
        check_company=False,
        help=(
            "Employees selected here will be visible to this user in "
            "attendance, regardless of employee company."
        ),
    )

    attendance_employee_count = fields.Integer(
        string="Attendance Employees",
        compute="_compute_attendance_employee_count",
    )

    @api.depends("employee_ids")
    def _compute_attendance_employee_count(self):
        for user in self:
            user.attendance_employee_count = len(user.employee_ids)

    def action_open_allowed_attendance(self):
        self.ensure_one()

        all_company_ids = self.env["res.company"].sudo().search([]).ids

        return {
            "type": "ir.actions.act_window",
            "name": "Allowed Employee Attendances",
            "res_model": "hr.attendance",
            "view_mode": "tree,form,pivot,graph",
            "domain": [("employee_id", "in", self.employee_ids.ids)],
            "context": {
                "allowed_company_ids": all_company_ids,
                "search_default_groupby_employee": 1,
            },
            "target": "current",
        }
