from odoo import models, fields

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    break_time = fields.Selection(
        selection=[
            ('15', '15 Minutes'),
            ('30', '30 Minutes'),
            ('45', '45 Minutes'),
            ('60', '60 Minutes'),
        ],
        string='Break Duration'
    )

    date_time = fields.Datetime(
        string='Date',
        help='The date on which the break was taken.'
    )
