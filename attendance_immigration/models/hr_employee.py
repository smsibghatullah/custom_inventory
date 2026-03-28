from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    immigration_rate = fields.Monetary(
        string="Immigration Rate",
        currency_field='currency_id'
    )
