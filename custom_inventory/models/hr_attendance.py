from odoo import models, fields, api
from odoo.addons.resource.models.utils import Intervals
from odoo.tools.float_utils import float_round
from pytz import timezone

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

    status = fields.Selection(
        selection=[
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
        ],
        string='Status',
        default='submitted'
    )

    approved_hours = fields.Float(string='Approved Hours')

    @api.depends('check_in', 'check_out', 'break_time')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                calendar = attendance._get_employee_calendar()
                tz = timezone(calendar.tz)
                check_in_tz = attendance.check_in.astimezone(tz)
                check_out_tz = attendance.check_out.astimezone(tz)
                lunch_intervals = attendance.employee_id._employee_attendance_intervals(
                    check_in_tz, check_out_tz, lunch=True)
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - lunch_intervals
                delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)

                worked_hours = delta / 3600.0

                if attendance.break_time:
                    worked_hours -= int(attendance.break_time) / 60.0

                worked_hours = float_round(worked_hours, precision_digits=2)
                attendance.worked_hours = worked_hours

                if attendance.status == 'submitted':
                    attendance.approved_hours = worked_hours
            else:
                attendance.worked_hours = False

    def action_approve_attendance_bulk(self):
        for rec in self.filtered(lambda r: r.status == 'submitted'):
            rec.status = 'approved'
            rec.approved_hours = rec.worked_hours

    def action_approve_attendance(self):
        for rec in self:
            if rec.status == 'submitted':
                rec.status = 'approved'
                rec.approved_hours = rec.worked_hours
