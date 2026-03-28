from odoo import models, fields, api

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    currency_id = fields.Many2one(
        'res.currency',
        related='employee_id.currency_id',
        readonly=True,
        store=True
    )

    immigration_rate = fields.Monetary(
        string="Immigration Rate",
        related='employee_id.immigration_rate',
        currency_field='currency_id',
        store=True
    )

    immigration_submitted_hrs = fields.Float(
        string="Immigration Submitted Hours",
        compute='_compute_hours',
        store=True
    )

    immigration_approved_hrs = fields.Float(
        string="Immigration Approved Hours",
        compute='_compute_hours',
        store=True
    )

  
    @api.depends('worked_hours', 'immigration_rate', 'employee_id.hourly_cost')
    def _compute_hours(self):
        for rec in self:
            worked_hours = rec.worked_hours or 0
            hourly_cost = rec.employee_id.hourly_cost or 1
            rate = rec.immigration_rate or 1  
            print(rate,"rate,",hourly_cost,"hourly_cost",worked_hours,"worked_hours",rec.approved_hours ,"rec.approved_hours ")
            print((rec.approved_hours * hourly_cost) / rate,"==================================================(rec.approved_hours * hourly_cost) / rate")
            print((worked_hours * hourly_cost) / rate,"==================================================(worked_hours * hourly_cost) / rate")

            rec.immigration_submitted_hrs = (worked_hours * hourly_cost) / rate
            rec.immigration_approved_hrs = (rec.approved_hours * hourly_cost) / rate